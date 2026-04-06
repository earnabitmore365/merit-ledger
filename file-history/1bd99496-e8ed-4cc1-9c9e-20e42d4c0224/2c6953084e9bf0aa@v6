# BitMEX API 完整调研 + Adapter 修复方案

## Context
21策略并行系统首次实盘部署，SL 挂单报错 `"Invalid strategy: null"`。
全网搜索 BitMEX REST/WS API 文档后，确认根因 + 制定修复方案。

---

## 一、根因确认：Bug 4（SL 挂单 Hedge Mode 报错）

**错误**：`POST /api/v1/order` 返回 `{"error":{"message":"Invalid strategy: null"}}`

**根因**：`place_stop_loss()` 和 `place_take_profit()` 没有设置 `strategy` 字段。
Hedge Mode 下，**每一个订单都必须指定 `strategy: 'Long'` 或 `'Short'`**，告诉交易所这个订单作用于哪个仓位。

**当前代码（adapter.py L832-839）**：
```python
data = {
    'symbol': symbol,
    'side': 'Buy' if side == OrderSide.BUY else 'Sell',
    'orderQty': contracts,
    'stopPx': stop_price,
    'ordType': 'Stop',
    'execInst': 'Close,LastPrice',
    # ❌ 缺少 strategy 字段！
}
```

**修复**：加一行 `strategy`：
```python
# 平多仓(Sell) → 作用于 Long 仓位 → strategy='Long'
# 平空仓(Buy) → 作用于 Short 仓位 → strategy='Short'
data['strategy'] = 'Long' if side == OrderSide.SELL else 'Short'
```

**同样修复 `place_take_profit()`**。

---

## 二、修改清单

### 文件：`lab/src/exchange/bitmex/adapter.py`

**改动 1：place_stop_loss 加 strategy**
- 位置：L832-839 的 data dict
- 加：`'strategy': 'Long' if side == OrderSide.SELL else 'Short'`

**改动 2：place_take_profit 加 strategy**
- 位置：L867-875 的 data dict
- 加：`'strategy': 'Long' if side == OrderSide.SELL else 'Short'`

### 验证
1. `py_compile adapter.py`
2. SCP 到 Vultr
3. 启动 1 个策略验证（VERIFY_MODE=True）
4. 等开仓后观察 SL 是否成功挂单（日志应显示 `SL 已挂` 而不是 `SL 挂单跳过`）

---

## 三、BitMEX API 完整参考（搜索结果汇总）

### 3.1 REST API — 下单 (`POST /api/v1/order`)

#### 参数完整表

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | ✅ | 合约代码（XBTUSDT, ETHUSDT 等） |
| side | string | | Buy / Sell |
| orderQty | int | | 合约数量（正数=买，负数=卖） |
| price | double | | 限价（Limit/StopLimit/LimitIfTouched） |
| stopPx | double | | 触发价（Stop/StopLimit/MarketIfTouched/LimitIfTouched） |
| ordType | string | | 订单类型（见下表） |
| execInst | string | | 执行指令，逗号分隔（见下表） |
| strategy | string | | **Hedge Mode 必填**：Long / Short |
| timeInForce | string | | Day/GoodTillCancel(默认)/ImmediateOrCancel/FillOrKill |
| clOrdID | string | | 客户端订单ID（最长36字符） |
| clOrdLinkID | string | | 关联订单分组ID（OCO/OTO 用） |
| contingencyType | string | | OneCancelsTheOther / OneTriggersTheOther |
| pegPriceType | string | | PrimaryPeg / MarketPeg / TrailingStopPeg |
| pegOffsetValue | double | | Peg 偏移值 |
| displayQty | int | | 显示数量（0=隐单/冰山单） |
| text | string | | 订单备注 |

#### ordType 完整列表

| ordType | 说明 | 必需参数 |
|---------|------|---------|
| **Market** | 市价单 | orderQty |
| **Limit** | 限价单（默认） | orderQty, price |
| **Stop** | 止损触发后市价 | orderQty, stopPx |
| **StopLimit** | 止损触发后限价 | orderQty, stopPx, price |
| **MarketIfTouched** | 触价市价（止盈用） | orderQty, stopPx |
| **LimitIfTouched** | 触价限价（止盈用） | orderQty, stopPx, price |
| **Pegged** | 浮动挂单 | pegPriceType, pegOffsetValue, execInst=Fixed |

#### execInst 完整列表

| execInst | 说明 |
|----------|------|
| ParticipateDoNotInitiate | Post-Only（只做 Maker，会吃单则拒绝） |
| ReduceOnly | 只减仓，不增仓 |
| **Close** | 平仓（隐含 ReduceOnly + 取消同方向限价单） |
| LastPrice | 用最新成交价触发 |
| MarkPrice | 用标记价格触发 |
| IndexPrice | 用指数价格触发 |
| LastWithinMark | Last 触发但限制在 Mark 价格带内 |
| Fixed | Pegged 单必需 |

> **Close vs ReduceOnly**：Close 包含 ReduceOnly 功能，但额外会**取消同方向的冲突限价单**

#### strategy 字段（Hedge Mode）

| 操作 | side | strategy | 说明 |
|------|------|----------|------|
| 开多 | Buy | Long | 开多头仓位 |
| 开空 | Sell | Short | 开空头仓位 |
| 平多 | Sell | Long | 卖出平多头 |
| 平空 | Buy | Short | 买入平空头 |
| 止损(多) | Sell | Long | 止损平多头 |
| 止损(空) | Buy | Short | 止损平空头 |
| 止盈(多) | Sell | Long | 止盈平多头 |
| 止盈(空) | Buy | Short | 止盈平空头 |

### 3.2 止损止盈实现方式

**方式 1：独立 Stop 单**（当前使用）
```python
# 多头止损
data = {
    'symbol': 'ETHUSDT',
    'side': 'Sell',
    'orderQty': 480800,
    'stopPx': 1872.0,        # 触发价
    'ordType': 'Stop',
    'execInst': 'Close,LastPrice',
    'strategy': 'Long',       # ← 这就是缺的那个字段
}
```

**方式 2：OCO 对（SL+TP 互取消）**
```python
# SL
{'symbol':'ETHUSDT', 'side':'Sell', 'orderQty':480800,
 'stopPx':1872, 'ordType':'Stop', 'execInst':'Close,LastPrice',
 'strategy':'Long',
 'clOrdLinkID':'eth-sl-tp-001', 'contingencyType':'OneCancelsTheOther'}
# TP
{'symbol':'ETHUSDT', 'side':'Sell', 'orderQty':480800,
 'stopPx':2200, 'ordType':'MarketIfTouched', 'execInst':'Close,LastPrice',
 'strategy':'Long',
 'clOrdLinkID':'eth-sl-tp-001', 'contingencyType':'OneCancelsTheOther'}
```

**方式 3：Trailing Stop（跟踪止损）**
```python
{'symbol':'ETHUSDT', 'side':'Sell', 'orderQty':480800,
 'stopPx': 2000,
 'ordType': 'Stop',
 'pegPriceType': 'TrailingStopPeg',
 'pegOffsetValue': -100,    # 追踪距离
 'execInst': 'Close,LastPrice',
 'strategy': 'Long'}
```

**⚠️ 不存在 `/position/tpsl` 端点** — 代码里的 TODO 是死路，用 Order API 即可。

### 3.3 杠杆设置

```
POST /api/v1/position/leverage
参数：
  symbol: 合约代码
  leverage: 0=全仓, 0.01~100=逐仓+固定杠杆
```

### 3.4 合约参数（需实时查 `/instrument`）

| 字段 | 说明 |
|------|------|
| underlyingToPositionMultiplier (u2p) | 1 币 = u2p 张合约 |
| lotSize | 最小下单量（合约数） |
| tickSize | 最小价格变动 |

> 各币种数值不同，必须通过 `GET /api/v1/instrument?symbol=XBTUSDT` 实时查询

### 3.5 REST API 限速

| 层级 | 限制 | 说明 |
|------|------|------|
| 分钟级 | 60 请求/分钟（认证） | 所有端点 |
| 秒级 | 10 请求/秒 | POST/PUT/DELETE 订单端点 |

**429 响应头**：`x-ratelimit-remaining-1s`、`retry-after`

### 3.6 WebSocket API

**连接**：`wss://ws.bitmex.com/realtime`

**认证**：
```python
signature = hex(HMAC_SHA256(secret, 'GET/realtime' + str(expires)))
{"op": "authKeyExpires", "args": ["API_KEY", expires, signature]}
```

**心跳**：ping/pong frames，5 秒间隔

**订阅限制**：**50 个 topic/连接**（我们用 18 太保守，可提到 40）

**订阅格式**：
```json
{"op": "subscribe", "args": ["tradeBin1m:XBTUSDT", "trade:ETHUSDT"]}
```

**公开频道**：tradeBin1m/5m/1h/1d, trade, quote, orderBookL2_25, orderBook10, instrument, liquidation, funding

**私有频道**（需认证）：order, execution, position, margin, wallet

**数据格式**：
- action: partial(初始快照) / insert / update / delete
- 每条消息含 table, action, data 字段

---

## 四、后续优化（不急，等系统稳定后）

1. **OCO 链接 SL+TP**：一个触发自动取消另一个，不用软件层管理
2. **TrailingStopPeg 替代软件 TTP**：交易所原生跟踪止损，延迟更低
3. **WS 订阅提到 40**：当前 BATCH_SIZE=18 太保守，可提到 40
4. **Dead Man's Switch**：`cancelAllAfter` 防止断网后仓位裸奔
