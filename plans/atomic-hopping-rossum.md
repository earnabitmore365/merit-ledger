# monitor_bot 升级：信号推送 + 战绩报告

## Context

1. 老板要实时看到策略信号变化（包括 HOLD），相同信号不重复推送
2. 老板要战绩报告：每小时一次 + 新开仓时额外推一次

## 改动

**文件**：`monitor_bot.py`（项目根目录）

### 改动1：信号变化实时推送

**加状态记忆**（main() 里，第 176 行附近）：
```python
last_signal = {}  # {coin: "signal_pos_regime"}
```

**在主循环 new_lines 处理后（第 227 行后）加**：
```python
# 策略信号变化推送（去重：信号+持仓+regime 任一变化才推）
if section_key in ('SOL', 'ETH', 'XRP') and new_lines:
    for line in reversed(new_lines):
        sm = re.search(
            r'信号=(\S+).*操作=(\S+).*持仓=(\S+).*余额=\$?([\d.]+).*regime=(\S+)',
            line)
        if sm:
            signal, action, pos, bal, regime = sm.groups()
            sig_key = f"{signal}_{pos}_{regime}"
            if sig_key != last_signal.get(coin, ''):
                last_signal[coin] = sig_key
                send_telegram(
                    f"📡 {coin} 信号={signal} 操作={action} "
                    f"持仓={pos} ${bal} regime={regime}")
            break
```

### 改动2：poll_logs 扩展（加全天交易统计）

在 `poll_logs()` 的 SSH 命令里加 3 条 grep，统计今天的开仓次数（不受 tail -50 限制）：

```python
cmd = (
    # ... 现有的 PROC + tail -50 ...
    f'echo "===SOL_TRADES==="; grep -c "操作=BUY\\|操作=SELL" logs/sol_1m_live.log 2>/dev/null || echo 0; '
    f'echo "===ETH_TRADES==="; grep -c "操作=BUY\\|操作=SELL" logs/eth_1m_live.log 2>/dev/null || echo 0; '
    f'echo "===XRP_TRADES==="; grep -c "操作=BUY\\|操作=SELL" logs/xrp_5m_live.log 2>/dev/null || echo 0; '
)
```

### 改动3：战绩报告（每小时 + 开仓时）

**战绩内容**：用 MCP 工具或 SSH 查 BitMEX 余额变化。但 monitor_bot 遵守零 API 原则，所以从日志提取：
- 当前余额（日志最新行的 `余额=$xxx`）
- 起始余额（$398.09，写死或从首条日志提取）
- 盈亏 = 当前 - 起始
- 今日交易次数（grep `操作=BUY\|操作=SELL` 计数）

**每小时报告**：`SUMMARY_INTERVAL` 改为 3600（当前是 900），摘要扩展加盈亏和交易次数。

**开仓时报告**：在 parse_events 检测到 `[TRADE]` 事件时，额外推一次战绩快报。

具体改动：

**加辅助函数**：
```python
INITIAL_BALANCE = 398.09  # 比赛起始余额

def build_performance_report(sections):
    """构建战绩报告"""
    # 当前余额
    current_bal = None
    for sk in ('SOL', 'ETH', 'XRP'):
        for line in reversed(sections.get(sk, [])):
            m = re.search(r'余额=\$?([\d.]+)', line)
            if m:
                current_bal = float(m.group(1))
                break
        if current_bal:
            break

    if current_bal is None:
        return None

    pnl = current_bal - INITIAL_BALANCE
    pnl_pct = (pnl / INITIAL_BALANCE) * 100

    # 今日交易次数（从 poll_logs 额外拉的全天统计，不是 tail -50）
    trade_count = 0
    for sk in ('SOL_TRADES', 'ETH_TRADES', 'XRP_TRADES'):
        try:
            trade_count += int(sections.get(sk, ['0'])[0].strip())
        except (ValueError, IndexError):
            pass

    emoji = "📈" if pnl >= 0 else "📉"
    return (
        f"{emoji} 战绩报告\n"
        f"余额: ${current_bal:.2f}\n"
        f"盈亏: ${pnl:+.2f} ({pnl_pct:+.1f}%)\n"
        f"今日交易: {trade_count}笔"
    )
```

**每小时摘要改为调用这个函数**（替换第 232-256 行的摘要逻辑）。

**开仓时额外推**：在 parse_events 检测到 `[TRADE]` 后，设一个 flag `trade_just_happened = True`，主循环检测到 flag 后推一次战绩。

## 验证

1. 重启 monitor_bot
2. Telegram 立刻收到 3 条信号状态（SOL/ETH/XRP 各一条，首次推送）
3. 等 15 分钟收到战绩报告（余额+盈亏+交易次数）
4. 信号不变时不重复推送
