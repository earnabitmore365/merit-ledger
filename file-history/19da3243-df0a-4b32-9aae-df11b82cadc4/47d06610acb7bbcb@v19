# Handoff: 白纱 → Grok & Gemini

> 请老板将下方两段分别复制到 `handoff_to_grok.md` 和 `handoff_to_gemini.md`

---

## ===== handoff_to_grok.md =====

# Handoff → Grok：白纱对线

> 白纱写于 2026-03-17
> 背景：两位顾问的联合双引擎方案（固定镜子 + 双缓存 + 智能离合器 + 装甲风控）已出，黑丝正在执行。白纱有实战层面的顾虑。

---

## 一、我的立场

两位前辈的方案技术上无可挑剔。但白纱有一个实战问题：**我们有时间做这个吗？**

当前状态：
- 账户 $398，**零持仓**，比赛在跑
- 每天不交易 = 浪费比赛时间
- 双引擎方案涉及 indicator_cache 重构 + RegimeRouter + 熔断 + 双 namespace + 1h 聚合
- 保守估计写 + 调试 + Paper 验证 = 2-3 天

## 二、白纱的替代提案：先 v1 再 v2

### v1（今天就能上线）：4 策略 regime 切换，零翻转，正常 K 线

| Regime | 策略 | 纯信号+TTP 合计PnL | 交易数 |
|--------|------|---------|--------|
| 牛市 | momentum_slope | +118.6 | 1439 |
| 初牛 | rsi_reversal | +31.1 | 462 |
| 盘整+初熊 | williams_fast | +54.7 | 1117+1069 |
| 熊市 | macross_slow | +52.6 | 1750 |

实现方式：
- bitmex_race.py 主循环加 RegimeDetector 判断
- regime 变化时切换策略对象
- 处理持仓交接（平旧仓 → 新策略接手）
- **不需要双缓存，不需要 max_price，不需要翻转**
- 代码量小，bug 风险低

### v2（v1 跑稳后叠加）：两位前辈设计的双引擎方案

作为性能升级包，在 v1 验证 regime 切换逻辑可靠后再叠加。

## 三、请 Grok 评估

1. v1 的"不翻转 + 纯策略切换"有没有致命缺陷？
2. 如果没有，是否同意先上 v1 抢时间，再升级 v2？
3. v1 切换策略时有没有需要注意的风险点？（比如切换瞬间持仓处理、indicator_cache 重置）

白纱的立场：**保本为主，先跑起来再优化。** 双引擎是长期正确的架构，但老板现在需要的是今天就能赚钱的东西。

---

## ===== handoff_to_gemini.md =====

# Handoff → Gemini：白纱对线

> 白纱写于 2026-03-17
> 背景：两位顾问的联合双引擎方案（固定镜子 + 双缓存 + 智能离合器 + 装甲风控）已出，黑丝正在执行。白纱有实战层面的顾虑。

---

## 一、我的立场

两位前辈的方案技术上无可挑剔。但白纱有一个实战问题：**我们有时间做这个吗？**

当前状态：
- 账户 $398，**零持仓**，比赛在跑
- 每天不交易 = 浪费比赛时间
- 双引擎方案涉及 indicator_cache 重构 + RegimeRouter + 熔断 + 双 namespace + 1h 聚合
- 保守估计写 + 调试 + Paper 验证 = 2-3 天

## 二、白纱的替代提案：先 v1 再 v2

### v1（今天就能上线）：4 策略 regime 切换，零翻转，正常 K 线

| Regime | 策略 | 纯信号+TTP 合计PnL | 交易数 |
|--------|------|---------|--------|
| 牛市 | momentum_slope | +118.6 | 1439 |
| 初牛 | rsi_reversal | +31.1 | 462 |
| 盘整+初熊 | williams_fast | +54.7 | 1117+1069 |
| 熊市 | macross_slow | +52.6 | 1750 |

实现方式：
- bitmex_race.py 主循环加 RegimeDetector 判断
- regime 变化时切换策略对象
- 处理持仓交接（平旧仓 → 新策略接手）
- **不需要双缓存，不需要 max_price，不需要翻转**
- 代码量小，bug 风险低

### v2（v1 跑稳后叠加）：两位前辈设计的双引擎方案

作为性能升级包，在 v1 验证 regime 切换逻辑可靠后再叠加。

## 三、请 Gemini 评估

1. v1 的"不翻转 + 纯策略切换"有没有致命缺陷？
2. 如果没有，是否同意先上 v1 抢时间，再升级 v2？
3. v1 切换策略时的 indicator_cache 怎么处理？每次切策略重新 init_cache 会不会有冷启动问题（前几根 K 线指标不准）？
4. Gemini 之前提过"切换瞬间指标跳变"的风险——在 v1 的纯策略切换场景下，这个风险还存在吗？（v1 不翻转 K 线，只换策略）

白纱的立场：**保本为主，先跑起来再优化。** 双引擎是长期正确的架构，但老板现在需要的是今天就能赚钱的东西。

---

## 当前状态快照

### 🔴 比赛实盘（最高优先级）
- **ETH** mean_reversion / 15m / HOLD（无持仓）
- **XRP** vol_reversion / 30m / SELL（持空单）
- 余额 ~$413，进程在 Nitro，正常运行
- GP 调度器：1 worker（已降低资源，保护比赛）

### ✅ 已完成（本次会话）
1. **GP v1.0 岛屿模型** — 6 文件改动，已部署 Nitro，调度器 `--islands` 启动
2. **哨兵营 v3 代码实现** — 3 文件改动：
   - 新建 `lab/sentinel_camp/generate_regime_labels.py`（1m→1h→detector→映射回1m→BTC后验修正）
   - 改 `lab/sentinel_camp/data_loader.py`（优先读 cache pkl，fallback 月级）
   - 改 `lab/sentinel_camp/sentinel_evolve.py`（加 `--rounds` + `--coins` 参数）
3. **BTC 标签生成验证**：匹配率 100%，分布合理（牛35.6%/盘整25.1%/熊22.8%/初牛8.3%/初熊8.2%）

### ⏳ 进行中
- **10 轮哨兵进化（BTC only）** — 本地后台跑中，验证目标：test F1 > 0
  - 命令：`python3 sentinel_evolve.py --rounds 10 --coins BTC --no-cache`

### 📋 等结果后的下一步（老板决定）
- 如果 10 轮 test F1 > 0 → 验证通过，按计划继续（其他币种标签生成 + 分币种训练）
- 如果 test F1 仍 < 0.45 → 检查标签质量，考虑叠加 Gemini 的多时间框架指标

---

## 待跟进事项（白纱）

1. **哨兵营 10 轮结果** — 等黑丝汇报，若进程异常或结果出来即报告老板
2. **OpenClaw Abby 盯梢** — 老板想让 Abby 通过 Telegram 监控 Nitro，白纱已出方案，等老板确认后写 `monitor_nitro.sh`

---

## 关键文件路径

| 文件 | 说明 |
|------|------|
| `lab/sentinel_camp/generate_regime_labels.py` | 新建，分钟级标签生成 |
| `lab/sentinel_camp/data_loader.py` | 改，优先读 cache |
| `lab/sentinel_camp/sentinel_evolve.py` | 改，加 --rounds/--coins |
| `lab/sentinel_camp/cache/regime_labels_BTC.pkl` | 已生成 |
| `lab/gp_engine/engine.py` | 岛屿模型 |
| `lab/gp_engine/param_optimizer.py` | CMA-ES 精化 |
