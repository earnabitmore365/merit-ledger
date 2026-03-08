# 文档更新 + 种子报告实现计划

## Context

**Phase A（先做）**：用户要求先更新 CHECKPOINT.md、CLAUDE.md/README.md，推送到 GitHub。
当前 git 有大量未提交改动：backtest.py（固定注码+翻倍指标）、run_full_matrix.py（全矩阵回测v2）、regime v2（ADX三层复合+滞后阈值）、CHECKPOINT.md（新文件）。

**Phase B（后做）**：生成**完整种子报告**（SQLite），包含：
1. 汇总指标（已有）
2. 每笔交易明细（开仓→平仓配对，含入场价/出场价/PnL/R值）
3. 每笔交易的 regime 标签（开仓时刻的 bull/bear/ranging）

目的：**一次跑完，以后所有分析直接从种子读取，永远不用重跑回测。**

用户原则：追求完整性、真实性、准确性。

---

## Phase A：文档更新 + GitHub 推送

### A1. 更新 CHECKPOINT.md

改动要点：
- 任务 7 "整合指标进交易系统" → ✅ 已完成（Regime v2 ADX 三层实现 + MarketScore 辅助）
- 新增任务 8 ✅ "全矩阵回测 v2"（1720组固定注码，含翻倍指标）
- 新增任务 9 ⬜ "种子报告"（当前目标，详细方案见下方 Phase B）
- 删除"等待 Sonnet 出详细实施方案"等过时内容
- 更新版本号为 v1.7

### A2. 更新 CLAUDE.md

改动要点：
- Backtest System 部分加入：固定注码模式（fixed_bet）、翻倍时间指标、`run_full_matrix.py` 全矩阵脚本
- 加入 Regime Detection v2 说明（ADX 三层复合 + 滞后阈值）
- 版本号更新

### A3. 更新 README.md

改动要点：
- 目录结构加入 `run_full_matrix.py`、regime/ 目录
- 新增 2.11 Regime Detection 章节
- 新增 5.4 全矩阵回测说明
- 更新日志加 v1.7
- 版本号更新

### A4. Git commit + push

```bash
git add src/backtest/backtest.py src/backtest/run_full_matrix.py \
        src/trading/regime/ CHECKPOINT.md CLAUDE.md README.md
git commit -m "v1.7: Regime v2 + 全矩阵回测 + 固定注码 + 翻倍指标"
git push
```

注意：排除 reports/（大文件）、error.log、indicators/cache/、download_1m_data.py（一次性脚本）

---

## Phase B：种子报告实现（commit 后执行）

## 存储格式：SQLite

单文件 `reports/seed_report.db`，理由：
- Python stdlib 内置 sqlite3，零依赖
- 可 SQL 查询（`SELECT ... WHERE regime='bull' AND strategy='proc'`）
- 比 JSON 小 60%（预估 600-800MB vs 1.8GB JSON）
- 单文件好管理，支持事务（中断可恢复）

## 数据库 Schema

```sql
-- 1. 汇总表（~1720 行）
CREATE TABLE combo_summary (
    id INTEGER PRIMARY KEY,
    strategy TEXT, coin TEXT, interval TEXT,
    total_return REAL, final_balance REAL,
    max_drawdown REAL, sharpe_ratio REAL, sortino_ratio REAL, calmar_ratio REAL,
    total_trades INTEGER, winning_trades INTEGER, losing_trades INTEGER,
    win_rate REAL, avg_win_pct REAL, avg_loss_pct REAL, profit_factor REAL,
    ttp_count INTEGER,
    double_count INTEGER, fastest_double_days REAL, avg_double_days REAL,
    daily_open_positions REAL
);

-- 2. 配对交易表（~850万行，核心数据）
CREATE TABLE paired_trades (
    id INTEGER PRIMARY KEY,
    combo_id INTEGER REFERENCES combo_summary(id),
    open_candle_idx INTEGER,    -- K线索引（用于精确定位）
    close_candle_idx INTEGER,
    open_time TEXT,             -- '%Y-%m-%d'
    close_time TEXT,
    holding_bars INTEGER,       -- 持仓K线数
    direction TEXT,             -- 'long' / 'short'
    entry_price REAL,
    exit_price REAL,
    capital REAL,               -- 下注本金
    position_size REAL,         -- capital × leverage
    pnl REAL,
    r_value REAL,               -- pnl / capital
    balance_after REAL,
    close_type TEXT,            -- 'ttp' / 'stop_loss' / 'signal' / 'liquidation' / 'end_of_data'
    regime_at_open TEXT         -- 'bull' / 'bear' / 'ranging' / 'unknown'
);
CREATE INDEX idx_pt_combo ON paired_trades(combo_id);
CREATE INDEX idx_pt_regime ON paired_trades(regime_at_open);

-- 3. Regime 时间线（~67万行，每根K线的regime标签）
CREATE TABLE regime_timeline (
    coin TEXT, interval TEXT,
    candle_idx INTEGER,
    candle_time_ms INTEGER,     -- 毫秒时间戳
    regime TEXT,
    adx REAL, sma_direction TEXT
);
CREATE UNIQUE INDEX idx_rt ON regime_timeline(coin, interval, candle_idx);

-- 4. 运行元数据
CREATE TABLE run_metadata (key TEXT PRIMARY KEY, value TEXT);
```

## 需要改的文件（2个）

### 1. `src/backtest/backtest.py` — 最小改动

**a) `__init__` 加 `candles` 参数**（避免重复从磁盘加载）：
```python
def __init__(self, ..., candles: List[Dict] = None):
    ...
    if candles is not None:
        self.candles = candles
    else:
        self.candles = self._load_data()
```

**b) 追踪每笔交易的 K 线索引**：
```python
self.trade_candle_indices: List[int] = []
```
在每个 `self.trades.append(...)` 处同时 `self.trade_candle_indices.append(i)`。
约 15 处需要加（所有 Trade append 点）。

### 2. 新建 `src/backtest/generate_seed.py` — 种子生成脚本

## 脚本结构

```
generate_seed.py
├── build_regime_timeline(klines, interval, config)
│   → 独立函数，复制 RegimeStrategy 的滞后逻辑
│   → 不实例化任何 Strategy 子类
│   → 输入 K 线，输出每根的 regime 标签
│
├── pair_trades(trades, candle_indices, regime_timeline, leverage)
│   → 将原始 Trade 配对（open + close = 1笔完整交易）
│   → 计算 R 值、查找 regime 标签、判断平仓类型
│
├── save_to_db(db, combo_summary, paired_trades, regime_timeline)
│   → SQLite 批量写入
│
└── main()
    → 三层循环：coin(10) → interval(4) → strategy(43)
    → 每个 (coin, interval) 只加载一次 K 线 + 计算一次 regime
    → 43 个策略共享同一份 regime 标签
```

## 循环顺序（关键优化）

```
for coin in COINS:                    # 10
    for interval in INTERVALS:        # 4
        candles = load_once()         # ← 只加载一次
        regime = compute_once()       # ← 只算一次（~67秒/1m）
        save_regime_to_db()

        for strategy in STRATEGIES:   # 43
            engine = BacktestEngine(candles=candles, ...)
            result = engine.run_backtest(strategy)
            paired = pair_trades(result.trades, ...)
            save_to_db(paired)

        db.commit()                   # 每 (coin,interval) 提交一次
```

## 交易配对算法

```python
open_trade = None
paired = []
for i, trade in enumerate(trades):
    if trade.order_type in ('BUY', 'SELL'):
        open_trade = (trade, candle_indices[i])
    elif trade.order_type in ('CLOSE_BUY','CLOSE_SELL','TTP_CLOSE_BUY','TTP_CLOSE_SELL','LIQUIDATION'):
        if open_trade:
            direction = 'long' if open_trade[0].order_type == 'BUY' else 'short'
            close_type = classify_close(trade)  # ttp/stop_loss/signal/liquidation
            r_value = trade.pnl / open_trade[0].capital
            regime = regime_timeline[open_trade[1]]['regime']
            paired.append({...})
            open_trade = None
```

平仓类型判定：
- `TTP_CLOSE_*` → 'ttp'
- `LIQUIDATION` → 'liquidation'
- `CLOSE_*` 且 pnl ≈ -capital → 'stop_loss'（止损PnL = -capital×leverage×stop_loss_pct = -capital）
- 其他 `CLOSE_*` → 'signal'

## Regime 时间线计算

独立函数，逻辑等价于 `RegimeStrategy` 但不加载子策略：

1. `detector.detect_with_details(window)` → ADX + SMA方向
2. 滞后阈值：趋势中 ADX<18 才退出，ranging 中 ADX>25 才进入趋势
3. 禁止 bull↔bear 直接翻转（必须经过 ranging）
4. min_dwell_bars=48 + confirm_bars=6
5. ADX 周期按 interval 缩放：1m→48, 5m→32, 15m→28, 1h→14

## 运行时间估算

| 阶段 | 时间 | 说明 |
|------|------|------|
| K线加载（40次） | ~20秒 | OS缓存后快 |
| Regime计算（40次） | ~15分钟 | 1m数据主要耗时 |
| 回测（1720组） | ~45分钟 | 与当前持平 |
| 配对+写入DB | ~5分钟 | 批量INSERT |
| **总计** | **~65分钟** | |

## 验证方案

1. 跑完后检查：`SELECT COUNT(*) FROM paired_trades` → 应有~850万行
2. 抽查一个 combo：对比 `paired_trades` 的汇总 vs `combo_summary` 的指标
3. Regime 分布检查：`SELECT regime, COUNT(*) FROM regime_timeline GROUP BY regime`
4. 跑一个 regime 分析查询，验证数据可用性

## 种子报告能回答的问题（不用重跑）

- 每个策略在 bull/bear/ranging 下的表现 → **数据驱动 regime_map**
- 不同注码方式（固定/复利/Kelly）的模拟 → 从 R 值重算
- TTP 有效性分析（按 regime/策略/持仓时长）
- 止损触发率 vs 信号平仓率
- 持仓时间与收益关系
