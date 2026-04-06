# 21 策略并行交易系统 — 完整实施方案

> 黑丝，2026-03-22
> 基于顾问最终架构 handoff（1141行），经老板确认+纠正

---

## 一、核心设计决策（顾问确认 + 老板纠正）

| 决策 | 最终结论 |
|------|---------|
| 保证金模式 | **全仓（Cross Margin）**——Hedge Mode只支持全仓 |
| 止损 | **交易所挂止损单（±10%）为主**，不需要软件层止损。脚本挂了也能触发 |
| TTP | **软件算移动位 → 交易所挂/更新止盈单**。软件动脑，交易所动手 |
| 限价重试 | **按周期区分**：SMALL_TF={'1m','5m'}每次重挂前重算信号，15m+直接排队 |
| 注码 | `max(100, available_margin // 21 // 10 * 10)`，用available margin算 |
| 多策略同时触发 | 先到先得，不排优先级 |
| 崩溃恢复 | 检查每个策略干到哪了，补完。不是无脑撤单 |
| 测试网 | 不用，直接主网 |

---

## 二、新建文件（6个）

| 文件 | 行数估算 | 职责 |
|------|---------|------|
| `lab/team_config.py` | ~60 | 21策略配置表（币种+策略名+周期+mirror标志）|
| `lab/kline_dispatcher.py` | ~250 | REST预下载250根×各周期 + UTC对齐 + 1m→高周期聚合 + 分发 |
| `lab/strategy_runner.py` | ~300 | 单策略容器：Mirror包装 + TTP + 止损挂单 + 止盈更新 + 状态管理 |
| `lab/limit_executor.py` | ~120 | 限价+5次重试+按周期重算信号+转市价 |
| `lab/trade_logger.py` | ~80 | 交易记录写SQLite（paired_trades格式）|
| `lab/unified_trader.py` | ~400 | 主脚本：ZMQ接收 + 资金管理 + 执行 + 熔断 + 对账 + 崩溃恢复 |

---

## 三、复用清单（不重复造轮子）

| 现有模块 | 路径 | 复用方式 | 排查结果 |
|---------|------|---------|---------|
| BitMEXAdapter | lab/src/exchange/bitmex/adapter.py | 直接用，已有strategy字段+reduce_only | ✅ 已排查 |
| 策略文件×103 | lab/src/core/strategy/strategy_*.py | registry自动加载 | ✅ 已有机制 |
| MirrorStrategy | lab/src/core/strategy/mirror.py | 包装mirror策略 | ✅ 已有 |
| TTPManager | lab/src/core/risk/ttp.py | 每个Runner一个实例 | ✅ 已有 |
| indicator_cache | lab/src/core/indicator_cache.py | init_cache()初始化指标窗口 | ✅ 已有 |
| FeedClient（部分） | lab/src/data/feed_client.py | ZMQ SUB逻辑复用，聚合逻辑重写（修了UTC bug）| ⚠️ 聚合部分不复用 |

---

## 四、执行顺序（3 Phase + 前置清理）

### 阶段0：前置清理
1. mirror.py 的 init_cache 调用处加 `namespace='flipped'`（自己找行号，不硬编）
2. TRX数据清除：先统计数量报老板确认，确认后删K线+种子+缓存

### Phase 1：搭框架（先跑起来）
3. 写 team_config.py（21策略配置表）
4. 写 kline_dispatcher.py：
   - REST预下载（只下载有策略用到的coin×interval组合，错峰1秒间隔）
   - UTC总分钟数对齐（修了FeedClient的%3600 bug）
   - 1m→5m/15m/30m/1h聚合 + 分发
5. 写 strategy_runner.py：
   - __init__：创建策略实例 + MirrorStrategy包装 + TTPManager
   - on_bar：mirror翻转 → 策略产信号 → 返回信号
   - 持仓状态管理：position/entry_price/position_size/sl_order_id/tp_order_id
   - after_open：交易所挂止损单（±10%）
   - update_ttp_on_exchange：软件算TTP level → 撤旧挂新止盈单
   - before_close：平仓前撤止盈止损单
6. 写 unified_trader.py：
   - 启动流程（严格按顺序）：JSON恢复→查交易所→补完未完成操作→REST预下载→init_cache→对齐UTC→订阅ZMQ→对账
   - 主循环：ZMQ接收1m→KlineDispatcher分发→各策略on_bar→_execute
   - 资金管理：get_bet_amount(available_margin) + can_open()
7. 本地测试：21策略收到对应周期K线，指标正常计算

### Phase 2：接交易（能开单）
8. 接入BitMEXAdapter + Hedge Mode（strategy='Long'/'Short'）
9. limit_executor.py：
   - SMALL_TF = {'1m', '5m'}：重挂前重算信号
   - 15m+：直接排队重挂
   - 5次未成交→转市价
10. API限速器（RateLimiter，100次/分钟滑动窗口，留20次余量）
11. 状态持久化（JSON原子写入：.tmp→os.replace）
    - 含sl_order_id/tp_order_id，崩溃恢复时知道交易所有哪些挂单
12. trade_logger.py：每笔交易写SQLite（跟种子paired_trades同格式）
13. Telegram通知：开仓/平仓/熔断/每小时摘要
14. 部署Nitro + 分步验证：
    - Gateway改启动参数：--coins 9币种 --intervals 全1m
    - process_guard.sh：Gateway + unified_trader.py
    - 14a. 先只开1个策略（ETH mean_reversion_mirror 1m）
    - 14b. 确认全链路：信号→限价开仓→交易所挂止损单→TTP更新止盈单→信号平仓
    - 14c. 跑24小时无异常
    - 14d. 逐步加到21个

### Phase 3：风控（不爆仓）
15. 全局熔断：余额<$100→撤所有挂单→市价全平→Telegram报警
16. 开仓后交易所挂止损单（±10%）
17. TTP集成：软件算移动位→交易所挂/更新止盈单
18. 每小时对账：内部状态vs交易所仓位，偏差>0.01→Telegram报警（只报警不自动修）
19. 崩溃重启恢复（14.3）：
    - 从JSON恢复→查交易所挂单+持仓
    - pending_open+部分成交→市价补齐
    - pending_close→市价平完
    - 无主挂单→撤销
    - 跑一次对账
20. Gateway断线恢复（14.4）：
    - 收到RECONNECT→清buffer→重新预下载250根→对齐UTC
    - 有持仓策略补算信号→反向就平→同向就持有
21. 部分成交→市价补齐剩余
22. 24小时监控确认稳定

---

## 五、不要做的事（顾问明确列出）

1. 不建 Regime 检测
2. 不预分资金
3. 不限制同时持仓数
4. 不改 Gateway（只改启动参数）
5. 不改现有策略代码
6. 不做软件层止损（交易所挂单已兜底）

---

## 六、关键技术细节

### 开仓→持仓→平仓完整流程
```
信号 → can_open? → 限价开仓（重试） → 成功 → 挂止损单（±10%）
  → 持仓：每秒tick算TTP → TTP level变了 → 更新交易所止盈单
  → 平仓触发 → 先撤SL/TP单 → 信号平仓用限价，止损/TTP由交易所执行
  → 脚本崩了 → 交易所SL/TP单兜底
```

### 同币种多策略合并问题
BitMEX会把同币种同方向仓位合并。策略A/B/C各做多$200→交易所看到一个$600多仓。
- 内部必须自己跟踪每个策略的持仓
- 平仓用精确数量+reduce_only
- 每小时对账验证内部vs交易所一致

### WebSocket订阅量
9币种×(tradeBin1m+trade) + position + margin = 20 topic
BitMEX单连接上限内，不订阅instrument和orderBookL2_25

---

## 七、自审（对照 rules.md）

| 规则 | 检查 | 结果 |
|------|------|------|
| RUL-001 工作在lab | 所有新建文件在lab/ | ✅ |
| RUL-007 影响链路 | 不改现有策略代码，只新建+复用 | ✅ |
| RUL-008 创建后记录 | Phase完成后更新README+CHECKPOINT | ✅ |
| RUL-009 技术细节自己搞 | 不问老板技术问题 | ✅ |
| RUL-017 一次到位 | 完整3Phase+22步+6文件+复用清单+流程图 | ✅ |
| RUL-034 做了新工具就用 | DuckDB/Parquet已建好供查询用 | ✅ |
| RUL-035 先验证再建 | 顾问已做选人验证+筛选+相关性，数据说了算 | ✅ |
| RUL-036 不急着出方案 | 老板和顾问都确认完了才开工 | ✅ |
| RUL-037 读一遍就全读 | 1141行从头到尾全读完 | ✅ |
| 止损=交易所挂单 | ✅ 无软件层9.5% |
| 限价重试按周期区分 | ✅ SMALL_TF={'1m','5m'} |
| 全仓模式 | ✅ Cross Margin |
| 注码用available_margin | ✅ adapter.get_balance()['available'] |

✅ 自审通过（第1轮，零纰漏）
