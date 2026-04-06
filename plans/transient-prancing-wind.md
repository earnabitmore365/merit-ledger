# 每日自动更新管线：增量下载 + 增量回测 + 报告看板

## Context
老板要求每天自动下载最新K线并更新回测结果。当前回测必须跑4年全量。老板指出"旧的已经有了，从断点跑新数据就好了，其他的东西根据开关仓计算"。

老板的架构拆分：
- **信号种子**（paired_trades）：只管开仓关仓止盈止损，增量追加
- **报告种子**（combo_summary）：从信号种子重算，不需要重跑回测

---

## 管线架构

```
cron (每天定时)
  └→ daily_pipeline.py
       ├─ 阶段1: 下载最新K线（增量，现有脚本已支持）
       ├─ 阶段2: 增量回测（从断点续跑新K线，追加交易到信号种子）
       ├─ 阶段3: 重算报告种子（从完整 paired_trades 重算 combo_summary）
       └─ 阶段4: 生成 HTML 报告看板
```

---

## 步骤 1：断点状态表

新建 `backtest_checkpoint` 表：

```sql
CREATE TABLE backtest_checkpoint (
    strategy          TEXT NOT NULL,
    coin              TEXT NOT NULL,
    interval_         TEXT NOT NULL,  -- interval 是 SQL 关键字
    -- 回测引擎状态
    last_candle_time_ms  INTEGER NOT NULL,  -- 最后K线时间戳（用于对齐新数据）
    balance              REAL NOT NULL,
    position             TEXT NOT NULL,     -- NO_POSITION / BUY / SELL
    entry_price          REAL,
    position_open_bar    INTEGER,
    trade_capital        REAL,
    -- TTP 状态（JSON）
    ttp_state            TEXT,
    -- regime 状态机（JSON）
    regime_state         TEXT,
    -- 统计
    buy_signals          INTEGER DEFAULT 0,
    sell_signals         INTEGER DEFAULT 0,
    total_candle_count   INTEGER NOT NULL,
    updated_at           TEXT NOT NULL,
    PRIMARY KEY (strategy, coin, interval_)
);
```

**关键设计**：策略本身无状态（grep 验证94个策略都没有 self.last_/prev_/state/history/count）。只保存回测引擎的持仓/余额/TTP/regime 状态。

---

## 步骤 2：增量回测核心

**新文件**：`lab/incremental_backtest.py`

流程：
1. 加载完整K线（旧+新合并后的）
2. 查断点 → 无断点则全量跑
3. **用时间戳（不是索引）对齐断点位置**——K线文件可能前端被裁剪
4. init_cache 用完整K线（indicator_cache 的 candle_count 校验会自动重算指标）
5. 恢复回测引擎状态（余额/持仓/entry_price/position_open_bar/TTP/regime）
6. 从断点位置继续跑回测循环
7. **end_of_data 处理**：上次有持仓时产生的 end_of_data 强平交易需要先删除（数据延长了这笔不再有效），从持仓状态继续。余额链：取 end_of_data 之前的 balance_after 作为续跑起点
8. 新交易追加到 paired_trades
9. 数据末尾仍做 end_of_data 平仓（保证余额链完整），下次增量时再删
10. 保存新断点 + 更新 regime_timeline 新增部分

**纯信号 vs TTP**：支持两个库。通过参数 `--ttp` 区分，和 generate_seed.py 保持一致。

**写入位置**：直接更新主库（seed_v3.db / seed_v3_ttp.db）。断点机制保证可恢复，不需要额外的中间库。首次运行前备份主库。

---

## 步骤 3：汇总重算

**新文件**：`lab/refresh_summary.py`

从完整 paired_trades 重新计算 combo_summary 的 35 个字段。计算逻辑从 generate_seed.py 的 save_combo() 和 backtest.py 的 _calculate_result() 提取复用。

只重算有增量更新的 combo（通过 checkpoint 的 updated_at 判断）。

---

## 步骤 4：编排脚本

**新文件**：`lab/daily_pipeline.py`

```bash
python3 lab/daily_pipeline.py                    # 全量（13币×4周期×94策略）
python3 lab/daily_pipeline.py --coins ETH XRP    # 只跑指定币种
python3 lab/daily_pipeline.py --skip-download    # 跳过下载，只跑回测
python3 lab/daily_pipeline.py --ttp              # TTP 版本
```

Nitro 上 cron：每天定时运行。默认单线程（内存紧张 65%）。

---

## 步骤 5：HTML 报告看板

**新文件**：`lab/seed_dashboard.py`

参考 gp_dashboard.py 模式（内嵌 CSS+JS 的单文件 HTML）：
- 筛选：按策略/币种/周期下拉多选
- 排序：按 Sharpe/翻倍速度/胜率等列排序
- 对比：勾选多个 combo 并排对比
- 详情：点击展开交易列表
- 功能细节实操时再定

---

## 验证方法

**一致性验证（最关键）**：对同一个 combo，"从头全量跑 4 年"vs"跑前 3 年 + 增量跑最后 1 年"，所有交易记录必须完全一致。

选 3-5 个代表性 combo：
- 高频策略（大量交易）
- 持仓跨断点（断点时正在持仓）
- TTP 状态跨断点（TTP 正在追踪时断开）

---

## 关键文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `lab/incremental_backtest.py` | 新建 | 增量回测核心（断点保存/恢复/续跑/追加） |
| `lab/refresh_summary.py` | 新建 | 从 paired_trades 重算 combo_summary |
| `lab/daily_pipeline.py` | 新建 | 编排脚本（下载→回测→汇总→看板） |
| `lab/seed_dashboard.py` | 新建 | HTML 报告看板 |
| `lab/src/backtest/backtest.py` | 可能微改 | 复用回测循环逻辑，可能需加 restore_state() 方法让引擎从中间开始 |
| `lab/src/backtest/generate_seed.py` | 参考 | 复用 pair_trades/save_combo/schema，不改 |
| `lab/src/core/risk/ttp.py` | 参考 | TTPState 序列化/反序列化 |
| `download_latest_coins_2.0.py` | 不改 | 已支持增量下载 |

## 步骤 0：币种替换 TRX → HYPE

1. 删除 TRX K线数据：`src/backtest/data/historical/TRX/`
2. 修改 `download_latest_coins_2.0.py` 的币种列表：TRX → HYPE
3. 下载 HYPE 全量K线（4周期：1m/5m/15m/1h）
4. 确认 HYPE 在 Binance 有 HYPE/USDT 交易对
5. seed_v3.db 中 TRX 的旧回测数据保留（历史记录），HYPE 数据会在增量回测时生成

---

## 实现顺序

0. TRX → HYPE 币种替换（下载脚本 + K线数据）
1. 断点表 schema + 读写函数
2. incremental_backtest.py 核心
3. 一致性验证（全量 vs 增量对比）— 验证通过才继续
4. refresh_summary.py
5. daily_pipeline.py
6. seed_dashboard.py HTML 看板
7. cron 部署

## 自审清单

### 完整性
- [x] 断点表字段完整（余额/持仓/entry_price/position_open_bar/trade_capital/TTP/regime）
- [x] 纯信号 + TTP 两个库都支持（--ttp 参数）
- [x] end_of_data 处理：删旧 → 续跑 → 新末尾再做 end_of_data → 下次再删
- [x] regime_timeline 增量更新：regime 状态机变量保存在 checkpoint
- [x] 主库 vs 增量库：直接更新主库，首次前备份

### 真实性
- [x] "策略无状态"：grep 验证94个策略无 self.last_/prev_/state/history/count ✅
- [x] "indicator_cache 自动重算"：源码确认 candle_count 校验机制 ✅
- [x] 时间戳对齐：用 last_candle_time_ms 二分查找，不依赖索引

### 有效性
- [x] 验证方法明确：全量 vs 增量交易记录逐笔对比
- [x] 每日增量预计 < 30 分钟（13币×4周期×94策略，每策略几秒）
- [x] generate_seed.py 不改。backtest.py 可能需微改（加 restore_state 方法），实现时确认
