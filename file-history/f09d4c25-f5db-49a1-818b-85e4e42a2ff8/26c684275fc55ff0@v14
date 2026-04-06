# 1m 时间段拆分并行

## Context
1m 周期是矩阵最大瓶颈 — 210万根 K 线，每个 combo 跑 10-70 秒，12 币种 × 105 策略 = 1,260 个 combo 串行跑要十几小时。代码硬限制 1m 最多 1 个 worker（`if iv == '1m' and has_1m: continue`），即使内存够也不并行。

时间段拆分：把 210万根 K 线拆成 4 段（各~52.5万根），4 worker 并行跑同一个 coin/interval 的不同时间段，跑完合并。速度提升 ~3-4 倍。

## 关键发现（代码探索确认）

1. **BacktestEngine 已支持切片**：`candles=` 参数直接传切片，DAYS=0 不截取
2. **策略信号不依赖全局索引**：用最近 200 根窗口，相对索引
3. **indicator_cache**：切片 len 不同会导致 DB 缓存失效，每段重算。不影响正确性，只是无法复用缓存
4. **regime_timeline**：传切片时 rel_idx 从 0 开始，与 engine.candles 对齐
5. **balance 跨段不连续**：每段 engine 独立初始化 initial_capital
6. **combo_summary 不能分段合并**：total_return/drawdown/sharpe 等依赖完整 balance 曲线
7. **paired_trades 可以分段合并**：每笔交易独立，candle_idx 加 offset 转全局

## 方案

### 核心思路
只对 1m 周期启用时间段拆分。不改 BacktestEngine，只改 generate_seed.py 的调度层。

### 改动文件
- `lab/src/backtest/generate_seed.py` — 新增 `_worker_coin_interval_segmented()` + 修改调度逻辑

### 实现步骤

**1. 新增 `_split_candles(candles, n_segments, warmup)` 函数**

```python
def _split_candles(candles, n_segments=4, warmup=500):
    """把 K 线拆成 n 段，后 n-1 段前加 warmup 预热"""
    total = len(candles)
    seg_size = total // n_segments
    segments = []
    for i in range(n_segments):
        start = i * seg_size
        end = total if i == n_segments - 1 else (i + 1) * seg_size
        warmup_start = max(0, start - warmup) if i > 0 else start
        segments.append({
            'candles': candles[warmup_start:end],
            'warmup_count': start - warmup_start,  # 前多少根是预热
            'global_offset': warmup_start,  # 全局偏移（转换 candle_idx 用）
        })
    return segments
```

**2. 新增 `_worker_coin_interval_segmented()` 函数**

跟现有 `_worker_coin_interval()` 类似，但：
- 接收 `candles_slice`（已切好的切片）而不是自己加载
- 接收 `warmup_count` 和 `global_offset`
- 跑完后丢弃预热段内的交易（open_candle_idx < warmup_count 的）
- paired_trades 的 candle_idx 加 global_offset 转全局索引

**3. 修改 `_run_seed_parallel()` 调度逻辑**

当 interval == '1m' 且 workers >= 4 时：
- 主进程先加载完整 K 线（一次 JSON 读取）
- 调用 `_split_candles()` 拆成 4 段
- 把 4 段作为 4 个独立任务提交给 ProcessPoolExecutor
- 4 段跑完后，合并 paired_trades（candle_idx 已转全局）

**4. combo_summary 处理**

分段跑无法直接算 combo_summary（balance 不连续）。两个选择：

**选择 A（推荐）：分段只产 paired_trades，combo_summary 在合并后从 trades 重算**
- 从合并后的 paired_trades 按时间排序重算 balance 曲线
- 从 balance 曲线算 total_return, max_drawdown, sharpe 等
- 需要新增 `_rebuild_combo_summary_from_trades()` 函数

**选择 B：不用分段的 combo_summary，让现有单线程逻辑跑 combo_summary**
- 分段只加速 paired_trades 生成
- combo_summary 还是单线程从完整 K 线跑（会产生重复计算）
- 不推荐

**5. 吻合验证（老板要求的安全机制）**

在重叠区（warmup 段的后半部分）对比两段产生的交易：
- 第 1 段末尾 warmup 根内的交易
- 第 2 段预热区的交易（会被丢弃，但先保留用于对比）
- 两边交易的 open_time + direction + entry_price 一致 = 预热到位
- 不一致 → 扩大 warmup（500→1000）重试一次
- 再不一致 → 退回单线程跑这个 combo

**6. 删除 1m 硬限制**

第 1124-1126 行 `if iv == '1m' and has_1m: continue` — 改为：
- 如果启用时间段拆分：允许同一 coin/1m 的 4 个段并行
- 内存估算改为 `1900 / 4 = 475` MB/段

### 不改的文件
- `backtest.py` — 不改引擎，只传切片
- `backtest/data/` — 不改数据文件

### 风险
1. **indicator_cache DB 缓存失效**：4 段都要重算指标。这是额外开销，但指标计算本身很快（几秒），不影响总体提升
2. **跨段持仓强制平仓**：段末尾的持仓被引擎强制平仓，下一段预热区重新开仓。通过吻合验证检测

### 验证
1. 挑一个 combo（如 atr_combo BTC 1m），分别用分段和完整跑，对比 paired_trades 笔数和总 PnL
2. 吻合验证通过率 > 99%（大部分策略在 500 根预热后指标收敛）
3. 分段后的 combo_summary 与完整跑的对比（允许 < 0.5% 误差，因为边界交易）

### 自审（第1轮）
- ✅ 完整性-1：影响链路追踪（generate_seed.py 调度 → BacktestEngine 切片 → indicator_cache → pair_trades → merge）
- ✅ 真实性-2：关键发现全部从代码确认（函数签名、参数、行号）
- ✅ 有效性-1：不改引擎核心，只改调度层，改动最小
- ✅ 纪律-4：不糊弄 — combo_summary 跨段不连续的问题正面处理（从 trades 重算）
- ✅ 自审通过（第1轮，零纰漏）
