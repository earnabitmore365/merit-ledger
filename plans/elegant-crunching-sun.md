# 紧急：monitor_bot 删除 BitMEX API 调用

## 问题
monitor_bot.py 的 query_bitmex() 每 60 秒 SSH 到 Nitro 调 BitMEX REST API，导致 429 限速风暴，实盘策略瘫痪数小时。违反 RUL-027。

## 修复（3 处）
1. 删 `query_bitmex()` 函数（整个函数删掉）
2. 删 `check_pnl_milestones()` 函数（依赖 API 数据）
3. 每小时摘要改为从日志提取余额/持仓（不碰 API）
4. 删除 `last_pnl_check`、`last_milestones`、`PNL_CHECK_INTERVAL` 等相关变量

## 保留
- `poll_logs()` — SSH 读日志文件（tail），不调 API ✅
- 交易事件推送（[TRADE] 解析）✅
- 进程存活检测 ✅
- Regime/TTP/HALT 事件推送 ✅

## 自审通过（3 轮）
