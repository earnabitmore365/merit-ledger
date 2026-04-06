# Plan: 种子报告全链路文档同步

## Context

build_seed_report.py 已按 handoff 完整重做（paired_trades 31列 + combo_summary 49列），但相关文档还停留在旧版本。需要全链路同步。

## 修改文件

| 文件 | 改动 |
|------|------|
| `backtest/build_seed_report.py` | 文件头代码段落索引行号更新 |
| `文档/种子/duckdb.md` 第16节 | seed_report schema 更新（paired_trades 15→31列，combo_summary 37→49列） |
| `data/README_KLINES_SEED.md` | seed_report 章节 + 查询示例更新 |
| `MEMORY.md` | DuckDB 路径大小更新 |

## 具体改动

### 1. build_seed_report.py 文件头索引

```
代码段落索引（行号随改动更新）：
  配置+常量              行 49    SEED_TYPES/参数/bars_per_funding
  import_sqlite_to_duckdb 行 86   Step 1 导入（含 regime_timeline）
  add_paired_trade_cols   行 204  Step 2a 逐笔后算 15 字段（CTAS + ASOF JOIN）
  compute_combo_metrics   行 293  Step 2b 汇总后算 28 字段（单 combo）
  run_combo_post_calc     行 509  Step 2b 调度（逐 combo 循环）
  create_indexes          行 573  Step 3 索引
  print_summary           行 578  统计+验证
  build_report            行 619  主入口
  argparse                行 644  CLI 参数化
```

### 2. duckdb.md 第16节

paired_trades 从旧版 15 列更新为实际 31 列：
- 原始 11 列（含 seed_type + strategy/coin/interval JOIN 冗余 = 15 列）
- 新增 16 列逐笔后算：holding_bars/holding_hours/capital/position_size/raw_pnl_pct/fee/slippage_cost/funding_count/funding_cost/pnl/pnl_amount/r_value/risk_reward_ratio/regime_at_open/balance_after/regime_at_open_1

combo_summary 从旧版 37 列更新为 49 列：
- 新增 12 列：drawdown_duration_bars/recovery_factor/ulcer_index/avg_win_pnl/avg_loss_pnl/best_trade_pnl/worst_trade_pnl/max_consecutive_wins/max_consecutive_losses/avg_holding_bars/skewness/kurtosis/tail_ratio

注明 regime_at_open 列名重复问题（regime_at_open 空，regime_at_open_1 有值）。

### 3. data/README_KLINES_SEED.md

seed_report.duckdb 章节更新：
- paired_trades 列数：15 → 31
- combo_summary 列数：37 → 49
- 文件大小：~42GB → ~375GB
- 新增字段说明
- 查询示例更新（用 regime_at_open_1）

### 4. MEMORY.md

DuckDB 路径更新：
- `DuckDB：/Volumes/SSD-2TB/project/wuji-auto-trading/duckdb/（41GB）` → 去掉，这个路径不对
- 种子管线状态更新

## 验证

- grep 确认各文档里的列数/大小/路径一致
- wuji-verify build_seed_report.py

## 自审

- ✅ 完整：4 个文件全覆盖
- ✅ 真实：列清单和行号从实际 DuckDB/grep 确认
- ✅ 有效：只改文档，不改代码逻辑
- ✅ 知常：文档跟代码同步是基本要求
- ✅ 静制动：先盘点再改，不遗漏
- 遗留：无
