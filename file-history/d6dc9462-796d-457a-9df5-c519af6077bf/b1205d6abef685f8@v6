# 计划：多策略战队架构 — 初熊战队先上线

## Context

黑丝 handoff 完整读完（`lab/handoff_to_baisha.md`）。

**现状**：
- REGIME_MAP 临时修复已做（初熊 mode→normal），但低波动行情仍触不到阈值 → HOLD
- 老板提出新架构：多策略战队 + Hedge Mode 并行 + 回测数据驱动方向配置
- BitMEX Hedge Mode 已开启，adapter.py 已兼容 ReduceOnly

**架构原则（老板定）**：
1. RegimeBridge 只负责：检测 regime + 切换战队（不再控制 mirror / 方向过滤）
2. Mirror/non-mirror = 策略本身属性，不是系统参数
3. 每个 regime 有专属战队（2-5策略同时跑），各自独立开平仓

---

## 初熊战队候选（黑丝已从回测数据查出）

> 初熊 × 1m × SOL/ETH/XRP，按做多+做空盈亏两列分开

| 策略 | 币种 | 做多PnL | 做空PnL | 推荐方向 |
|------|------|---------|---------|---------|
| elder_ray_mirror | XRP | +22.4 | +0.2 | BOTH（多为主） |
| atr_combo | XRP | +3.1 | +7.8 | BOTH（空为主） |
| volume_momentum_mirror | SOL | +1.0 | +1.4 | BOTH |
| mass_index_mirror | ETH | +0.9 | +0.5 | BOTH |

**黑丝建议**：先每币种 1-2 个，初熊战队共 4 个策略进程。

---

## MVP 方案（Phase 1 — 立即可做）

**目标**：替换当前无效的3个 mean_reversion_mirror 进程 → 换成初熊战队4进程

**不改代码**：Hedge Mode + ReduceOnly 已支持，策略各自独立开平仓，零冲突。

### 资金分配

| 策略 | 币种 | 建议仓位 |
|------|------|---------|
| elder_ray_mirror | XRP | $100 |
| atr_combo | XRP | $100 |
| volume_momentum_mirror | SOL | $100 |
| mass_index_mirror | ETH | $98 |
| **合计** | | **$398** |

### process_guard.sh 改动

```bash
# 当前（无效，全程 HOLD）
python3 bitmex_race.py --feed --mirror --regime-bridge --strategy mean_reversion --coin SOL --interval 1m --min-bet 100
python3 bitmex_race.py --feed --mirror --regime-bridge --strategy mean_reversion --coin ETH --interval 1m --min-bet 100
python3 bitmex_race.py --feed --mirror --regime-bridge --strategy mean_reversion --coin XRP --interval 5m --min-bet 80

# 改后（初熊战队，双向开单，去掉 --regime-bridge）
python3 bitmex_race.py --feed --mirror --strategy elder_ray --coin XRP --interval 1m --min-bet 100
python3 bitmex_race.py --feed --mirror --strategy atr_combo --coin XRP --interval 1m --min-bet 100
python3 bitmex_race.py --feed --mirror --strategy volume_momentum --coin SOL --interval 1m --min-bet 100
python3 bitmex_race.py --feed --mirror --strategy mass_index --coin ETH --interval 1m --min-bet 98
```

注：去掉 `--regime-bridge`（新架构：RegimeBridge 不再控制方向过滤，策略自由双向）。

### 待验证（执行前必须确认）

1. **策略文件名**：`elder_ray_mirror` / `atr_combo` / `volume_momentum_mirror` / `mass_index_mirror` 在 `lab/src/strategy/` 下的实际文件名和注册名
2. **`--strategy` 参数格式**：bitmex_race.py 接受的策略名（`elder_ray`? `elder_ray_mirror`?）
3. **Nitro 上策略代码**：这些策略是否已同步到 `~/trading/` 下

---

## Phase 2：RegimeBridge 架构重构（中期，稳定后再做）

**目标**：RegimeBridge 只做 regime 检测 + 通知各进程当前 regime，各进程自己决定是否继续

**不在本次做**，等 Phase 1 初熊战队验证通过后。

---

## 执行步骤

1. **验证策略存在**：SSH Nitro，查 `~/trading/src/strategy/` 下有哪些策略文件
2. **确认 strategy 参数格式**：在 Nitro 上跑 `python3 bitmex_race.py --help` 查策略列表
3. 如果策略不存在 → 先同步 lab 策略到 Nitro
4. **编辑 process_guard.sh**：替换成4个新进程命令
5. **杀旧进程**（process_guard.sh 30秒自动拉起新进程）
6. **观察日志**：确认4个新进程正常启动、收到 K 线、产出信号
7. **观察 2 小时**：是否有实际开单（Hedge Mode 下多空并存）
