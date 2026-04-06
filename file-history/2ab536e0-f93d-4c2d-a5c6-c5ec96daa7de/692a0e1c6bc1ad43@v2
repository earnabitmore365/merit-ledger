# Trading MCP Server — 从 Feed Gateway 读数据

## Context

老板要给黑丝白纱装 MCP 工具，方便查账户余额、持仓、行情等。太极之前直接调 BitMEX API 的方案被老板否决——Feed Gateway 已经通过 WebSocket 实时缓存了这些数据，MCP 应该从 Gateway 读，不重复调 API。

**现有基础设施**：
- Feed Gateway（`lab/src/data/feed_gateway.py`）跑在 Nitro，通过 WebSocket 持续接收 K线/价格/持仓/余额
- Gateway 已缓存的数据：`_kline_windows`（K线）、`_last_price`（价格）、`_positions`（持仓）、`_margin`（余额）
- Gateway 的 ZMQ REP 端口（5556）目前只支持 `KLINES` 请求

**之前已完成但需要修改的文件**：
- `auto-trading/mcp_server.py` — 需要重写，从直接调 API 改为从 Gateway 读
- `auto-trading/.mcp.json` — 保留不变

## 两步走

### 第一步：黑丝扩展 Gateway（项目代码，黑丝负责）

**文件**：`lab/src/data/feed_gateway.py`

#### A. 全量订阅 — 加 3 个 WebSocket 频道

现在 `start()` 里订阅了 `tradeBin`、`trade`、`position`、`margin`、`order`。

加：
- `execution` — 账户成交记录（私有频道，加到 `subscribe_private` 或单独订阅）
- `instrument:{symbol}` — 合约信息（含资金费率、24h高低价、标记价、未平仓量）
- `orderBookL2_25:{symbol}` — 25 档深度

加对应缓存变量：
- `_executions: deque(maxlen=100)` — 最近 100 条成交
- `_instruments: Dict[str, dict]` — 合约信息（按 coin）
- `_orderbooks: Dict[str, dict]` — 深度（按 coin）

加 `_on_ws_table` 里对应的 handler（跟现有 position/margin 模式一样：update 时合并，delete 时清除）。

加 ZMQ PUB 广播：
- `EXEC {json}` — 成交
- `INSTRUMENT.{coin} {json}` — 合约信息
- `ORDERBOOK.{coin} {json}` — 深度

#### B. 扩展 REP 协议 — `_rep_loop` 加 6 个查询

| 请求 | 响应 | 数据来源 |
|------|------|---------|
| `KLINES {coin} {interval}` | K线 JSON 数组 | `_kline_windows`（已有） |
| `BALANCE` | 余额 JSON | `_margin` 缓存 |
| `POSITIONS` | 持仓 JSON 数组 | `_positions` 缓存 |
| `PRICE {coin}` | 价格浮点数 | `_last_price` 缓存 |
| `EXECUTIONS [count]` | 成交 JSON 数组 | `_executions` 缓存（新增） |
| `INSTRUMENT {coin}` | 合约信息 JSON | `_instruments` 缓存（新增） |
| `ORDERBOOK {coin}` | 深度 JSON | `_orderbooks` 缓存（新增） |

改动范围：`_rep_loop` 加 elif 分支，读缓存返回。

#### C. Gateway 改完后重启

黑丝在 Nitro 上重启 Gateway 进程，验证新频道数据正常接收。

---

### 第二步：太极写 MCP Server + 查询脚本

等黑丝 Gateway 改完后执行。

#### A. Nitro 端查询脚本

**文件**（新建）：`lab/src/data/gw_query.py`

轻量 CLI，跑在 Nitro 上：
```bash
python3 gw_query.py BALANCE
python3 gw_query.py POSITIONS
python3 gw_query.py PRICE SOL
python3 gw_query.py KLINES ETH 1m
python3 gw_query.py EXECUTIONS 20
python3 gw_query.py INSTRUMENT BTC
```

内部：连 localhost:5556 ZMQ REQ → 发请求 → 打印 JSON → 退出。

#### B. 重写 MCP Server

**文件**：`auto-trading/mcp_server.py`（覆盖之前直接调 API 的版本）

**数据流**：
```
Claude Code (Mac)
  → MCP Server (stdio)
    → SSH 到 Nitro
      → python3 gw_query.py {请求}
        → ZMQ REQ → Feed Gateway REP → 返回缓存数据
```

**5 个工具**（全部从 Gateway 读，零 API 调用）：

| 工具 | gw_query 参数 | 说明 |
|------|-------------|------|
| `get_balance` | `BALANCE` | 余额/保证金/未实现盈亏 |
| `get_positions` | `POSITIONS` | 所有持仓 |
| `get_recent_trades(count)` | `EXECUTIONS {count}` | 最近成交记录 |
| `get_market_data(coin)` | `PRICE {coin}` + `INSTRUMENT {coin}` | 价格+资金费率+24h数据 |
| `get_klines(coin, interval)` | `KLINES {coin} {interval}` | K线数据 |

## 关键文件

| 文件 | 操作 | 谁改 |
|------|------|------|
| `lab/src/data/feed_gateway.py` | 修改 `_rep_loop`，加 3 个查询类型 | 黑丝（项目代码） |
| `lab/src/data/gw_query.py` | 新建（Nitro 端查询 CLI） | 黑丝 |
| `auto-trading/mcp_server.py` | 重写（SSH + gw_query） | 太极 |
| `auto-trading/.mcp.json` | 保留不变 | — |

## 需要确认

1. **谁改 Gateway**：Gateway 是项目代码（在 lab/ 下），按规矩应该黑丝改。但太极也可以改（扩展 REP 协议是基础设施工作）。老板定。
2. **SSH 连接参数**：`.env.mcp` 已有 `NITRO_SSH_CMD=ssh -p 2222 ...`，确认这个还能用。
3. **Gateway 是否在跑**：需要 SSH 到 Nitro 验证 Gateway 进程状态。

## 验证

1. SSH 到 Nitro → `python3 gw_query.py BALANCE` → 返回余额 JSON
2. SSH 到 Nitro → `python3 gw_query.py POSITIONS` → 返回持仓 JSON
3. 黑丝/白纱新会话 → `/mcp` → 看到 trading server 连接
4. 黑丝问"查一下余额" → MCP 自动调用 `get_balance` → 返回数据（来自 Gateway 缓存，零 API 调用）
