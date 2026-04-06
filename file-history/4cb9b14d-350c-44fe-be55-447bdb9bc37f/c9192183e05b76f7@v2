# 监控修正 3 处方案

## Context
老板发现 3 个问题：TTP 百分比未乘杠杆 10x、PnL 自算不准（hardcode $1000）、开单漏推送（bitmex_race.py 用 print 不进日志）。
黑丝在 handofftotaiji.md 完成自审，交给白纱执行。

## 文件改动清单

### 1. ttp.py
**路径**：`/Volumes/BIWIN NV 7400 2TB/project/auto-trading/lab/src/core/risk/ttp.py`

**改动（行 149-173）：**
- 删除行 152-153（`_est_pnl` 估算注释 + 计算，只用于 PnL 显示，删掉）
- 行 162-163（🔥 利润新高）：`profit={profit_pct:.2%} PnL=${_est_pnl:+.2f}` → `profit={profit_pct*10:.1f}%`
- 行 172-173（🔻 亏损加深）：同上

**改后格式：**
```
[TTP Probe] 🔥利润新高! LONG profit=13.3% curr=88.7600
[TTP Probe] 🔻亏损加深! LONG profit=-13.3% curr=88.7600
```

**不改：** 里程碑触发频率（`profit_pct * 200`）保持未杠杆 0.5% 触发，心跳行 145 不改

---

### 2. bitmex_race.py
**路径**：`/Volumes/BIWIN NV 7400 2TB/project/auto-trading/lab/bitmex_race.py`

**改动 A — feed 模式（行 860-865）：**
```python
# 删除：
if action != 'NONE':
    print(f"\n  {'='*40}")
    print(f"  交易! {action}")
    print(f"  {args.coin} @ ${feed_client.get_price(args.coin):.2f}")
    print(f"  余额: {bal_str}")
    print(f"  {'='*40}\n")

# 改为：
if action != 'NONE':
    logger.info(
        f"[TRADE] {args.coin} {action} @ ${feed_client.get_price(args.coin):.2f} | "
        f"余额={bal_str} | {regime_str.strip()}")
```
注：`regime_str` 已在行 854 定义（`f" regime={bridge.regime}" if bridge else ""`），`.strip()` 去掉前导空格。

**改动 B — 非 feed 模式（行 899-904）：**
```python
# 删除：
if action != 'NONE':
    print(f"\n  {'='*40}")
    print(f"  交易! {action}")
    print(f"  {args.coin} @ ${adapter.get_price(args.coin):.2f}")
    print(f"  余额: {bal_str}")
    print(f"  {'='*40}\n")

# 改为：
if action != 'NONE':
    _regime_str = f"regime={bridge.regime}" if bridge else ""
    logger.info(
        f"[TRADE] {args.coin} {action} @ ${adapter.get_price(args.coin):.2f} | "
        f"余额={bal_str} | {_regime_str}")
```
注：非 feed 模式无 `regime_str`，局部定义 `_regime_str` 避免命名冲突。

---

### 3. monitor_bot.py
**路径**：`/Volumes/BIWIN NV 7400 2TB/project/auto-trading/monitor_bot.py`

**改动 A — 替换 🔵 为 📌**（行 99-106）：
旧 `操作=ACTION` → 🔵 解析保留会与新 `[TRADE]` → 📌 重复推送同一笔交易。
根据 handoff 推送对比表（改后只显示 📌），用 [TRADE] 解析替换 操作= 解析：
```python
# 删除 行 99-106 的 操作=ACTION 解析（🔵）
# 新增 [TRADE] 解析（📌）：
if '[TRADE]' in line:
    events.append(f"📌 {line.split('[TRADE]')[1].strip()[:80]}")
```

**改动 B — 🔥/🔻 去掉 PnL**（行 122-135）：
```python
# 原来：
if '[TTP Probe] 🔥利润新高' in line:
    m2 = re.search(r'profit=(\S+)', line)
    m3 = re.search(r'PnL=(\S+)', line)
    profit = m2.group(1) if m2 else ''
    pnl = m3.group(1) if m3 else ''
    events.append(f"🔥 {coin} 利润新高 {profit} ({pnl})")

if '[TTP Probe] 🔻亏损加深' in line:
    m2 = re.search(r'profit=(\S+)', line)
    m3 = re.search(r'PnL=(\S+)', line)
    profit = m2.group(1) if m2 else ''
    pnl = m3.group(1) if m3 else ''
    events.append(f"🔻 {coin} 亏损加深 {profit} ({pnl})")

# 改为：
if '[TTP Probe] 🔥利润新高' in line:
    m2 = re.search(r'profit=(\S+)', line)
    profit = m2.group(1) if m2 else ''
    events.append(f"🔥 {coin} 利润新高 {profit}")

if '[TTP Probe] 🔻亏损加深' in line:
    m2 = re.search(r'profit=(\S+)', line)
    profit = m2.group(1) if m2 else ''
    events.append(f"🔻 {coin} 亏损加深 {profit}")
```

---

## 执行顺序
1. 改 ttp.py（Nitro 上跑，改完需重启 3 策略进程）
2. 改 bitmex_race.py（同上）
3. 改 monitor_bot.py（Mac Mini 上跑，改完重启 monitor_bot）
4. SSH 上 Nitro 重启 3 策略进程（kill + nohup）
5. Mac Mini 重启 monitor_bot

## 验证
- Telegram 收到下一笔交易：格式为 `📌 SOL BUY @ $XX | 余额=$XXX | regime`
- TTP 新高/新低格式：`🔥 SOL 利润新高 13.3%`（无 PnL）
- 无重复推送（同一笔交易只有 📌，无额外 🔵）
