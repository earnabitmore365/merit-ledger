# 第3层排查 — 业务逻辑层 7 个 Bug 修复 + 全链路测试

## Context

Gateway ✅ 封板，Adapter ✅ 封板。顾问给了 layer3_audit.md，要求审查 unified_trader + strategy_runner + limit_executor + team_config 四个文件。

代码审查完成，发现 **7 个 bug**（4 个 P0 + 2 个 P1 + 1 个 P2）。最严重的是 Bug 1：**所有正常平仓操作根本不会平仓，而是开反向仓位**。

## 审查结论（非 bug 项确认正确）

- ✅ strategy_runner.py：全部正确（on_bar 返回 str, SL/TP 方向和 size 正确, 序列化完整）
- ✅ team_config.py：全部正确（21策略, MAX_BET=$1000保证金, LEVERAGE=10, 提款$27K/$6K）
- ✅ 对账 _reconcile()：单位一致（双方都是 coins）
- ✅ 熔断 _circuit_break()：size 和 reduce_only 正确
- ✅ 价格检查：在 state 变化前执行

---

## Bug 列表

### Bug 1 (P0-CRITICAL): 平仓不平仓，开反向仓

| 项 | 值 |
|---|---|
| **文件** | `limit_executor.py` + `unified_trader.py:291` |
| **问题** | `_close_position()` 调 `executor.execute_limit()`，executor 创建的 OrderRequest **没有 reduce_only=True**。Hedge Mode 下，SELL 没有 Close → adapter 设 `strategy=Short` → **开新空仓而不是平多仓** |
| **影响** | 所有信号平仓 / TTP平仓 都不会真正平仓，反而开反向仓位 |
| **修复** | executor 加 `reduce_only` 参数，平仓调用时传 True |

### Bug 2 (P0): _execute() 双重 u2p 转换

| 项 | 值 |
|---|---|
| **文件** | `unified_trader.py:256-260` |
| **问题** | `actual_size` 来自 executor，已经是 COINS。但代码当 contracts 再除 u2p → SOL: 0.01/10000=0.000001 |
| **影响** | position_size 极小 → SL/TP/平仓 size 极小 → 全部失败 |
| **修复** | 删掉 `/ u2p`，直接用 `actual_size` |

### Bug 3 (P0): executor 市价兜底双重转换

| 项 | 值 |
|---|---|
| **文件** | `limit_executor.py:182-186` |
| **问题** | adapter fix 后 `filled_size` 已是 COINS，但代码仍除 u2p → 双重转换 |
| **修复** | 直接用 `mkt_result.filled_size` |

### Bug 4 (P0): 崩溃恢复 cumQty 没转换

| 项 | 值 |
|---|---|
| **文件** | `unified_trader.py:432` |
| **问题** | `cumQty` 是合约数，`_target_size` 是币数量，直接相减 → remaining 错误 |
| **修复** | `filled = filled / u2p` |

### Bug 5 (P1): 无 JSON + 孤儿仓位

| 项 | 值 |
|---|---|
| **文件** | `unified_trader.py:_startup_recovery` |
| **问题** | JSON 不存在时只 return，不查交易所仓位。孤儿仓位无人管 |
| **修复** | 恢复末尾加孤儿仓位扫描+市价平仓 |

### Bug 6 (P1): 平仓失败后 state 不一致

| 项 | 值 |
|---|---|
| **文件** | `unified_trader.py:321-324` |
| **问题** | 平仓失败设 state='active'，但 position_size 可能已过时（部分成交） |
| **修复** | 失败后从交易所同步真实仓位大小 |

### Bug 7 (P2): 熔断余额判断脆弱

| 项 | 值 |
|---|---|
| **文件** | `unified_trader.py:361-365` |
| **问题** | `available > 1000` 启发式判断是微美元还是美元，不可靠 |
| **修复** | 改用 `adapter.get_balance()['available']`（REST，已是美元） |

---

## 修复步骤

### 步骤 1：修 limit_executor.py（Bug 1 + Bug 3）

**Bug 1 — 加 reduce_only 参数：**

```python
# line 43: 加参数
def execute_limit(self, strategy, side, size, adapter, dispatcher=None, reduce_only=False):

# line 76-82: 限价单加 reduce_only
order = OrderRequest(
    coin=strategy.coin, side=order_side, order_type=OrderType.LIMIT,
    size=size, price=price, reduce_only=reduce_only,
)

# line 125-130: 部分成交市价补齐加 reduce_only
mkt_order = OrderRequest(
    coin=strategy.coin, side=order_side, order_type=OrderType.MARKET,
    size=remaining, reduce_only=reduce_only,
)

# line 173-178: 5次失败转市价加 reduce_only
mkt_order = OrderRequest(
    coin=strategy.coin, side=order_side, order_type=OrderType.MARKET,
    size=size, reduce_only=reduce_only,
)
```

**Bug 3 — 删市价兜底双重转换（line 181-195）：**

```python
if mkt_result.success:
    # filled_size 已是币数量（adapter 内部已转换）
    mkt_filled_coins = mkt_result.filled_size or 0
    if mkt_filled_coins <= 0:
        mkt_filled_coins = size
    return {
        'success': True,
        'price': mkt_result.filled_price or 0,
        'actual_size': mkt_filled_coins,
        'attempts': self.MAX_RETRIES,
        'fallback': 'market',
    }
```

### 步骤 2：修 unified_trader.py（Bug 2 + Bug 1 调用端 + Bug 4 + Bug 5 + Bug 6 + Bug 7）

**Bug 1 调用端 — _close_position() 传 reduce_only=True（line 291-294）：**

```python
result = self.executor.execute_limit(
    strategy, close_side, strategy.position_size,
    self.adapter, self.dispatcher,
    reduce_only=True,
)
```

**Bug 2 — 删双重 u2p 转换（line 253-262）：**

```python
if result['success']:
    strategy.position = signal_str
    strategy.entry_price = result['price']
    # actual_size 已经是币数量（limit_executor 内部已转换）
    actual_size = result.get('actual_size', 0)
    strategy.position_size = actual_size if actual_size > 0 else coin_qty
```

**Bug 4 — 崩溃恢复 cumQty 转换（line 432 后）：**

```python
filled = float(pending[0].get('cumQty', 0) or 0)
# cumQty 是合约数，转成币数量
u2p = self.adapter._get_u2p(strategy.coin)
filled = filled / u2p if u2p > 0 else filled
```

**Bug 5 — 孤儿仓位扫描（line 505 后，_save_states 前）：**

```python
# 5. 检查孤儿仓位（内部 idle 但交易所有仓位 → 市价平仓）
try:
    exchange_positions = self.adapter.get_positions()
    internal_coins = {s.coin for s in self.strategies if s.position and s.position_size > 0}
    for pos in exchange_positions:
        if pos.coin not in internal_coins:
            logger.warning(f"⚠️ 孤儿仓位: {pos.coin} {pos.side} size={pos.size}，市价平仓")
            close_side = OrderSide.SELL if pos.side == 'LONG' else OrderSide.BUY
            try:
                self.adapter.place_order(OrderRequest(
                    coin=pos.coin, side=close_side, order_type=OrderType.MARKET,
                    size=pos.size, reduce_only=True))
            except Exception as e:
                logger.error(f"孤儿仓位平仓失败 {pos.coin}: {e}")
except Exception:
    pass
```

**Bug 6 — 平仓失败后同步仓位（line 321-324）：**

```python
else:
    strategy.state = 'active'
    # 从交易所同步真实仓位，防止 size 过时
    try:
        pos = self.adapter.get_position(strategy.coin)
        if pos and pos.size > 0:
            strategy.position_size = pos.size
            logger.warning(f"[{strategy.id}] 平仓失败，同步仓位 size={pos.size}")
        else:
            # 交易所无仓位 → 实际已平
            strategy.position = None
            strategy.position_size = 0
            strategy.state = 'idle'
            logger.info(f"[{strategy.id}] 平仓失败但交易所无仓位，视为已平")
    except Exception:
        pass
    logger.error(f"[{strategy.id}] 平仓失败: {result.get('reason', 'unknown')}")
    self._save_states()
```

**Bug 7 — 熔断用 REST 余额（line 361-365）：**

```python
try:
    balance = self.adapter.get_balance()  # REST，已是美元
    available_usd = balance.get('available', 0)
```

### 步骤 3：py_compile 验证

```bash
python3 -m py_compile lab/limit_executor.py
python3 -m py_compile lab/unified_trader.py
```

### 步骤 4：写 test_full_chain.py（5 场景）

按顾问模板写测试脚本，5 个场景：
1. **多头完整链路**：注码→限价开多→验证 position_size 是币数量→挂 SL→平仓（Close）→确认零仓位零挂单
2. **空头完整链路**：同上反向
3. **注码递增**：余额 $2100/$5000/$10500/$21000/$27000 各算一遍
4. **崩溃恢复**：开仓→存 JSON→模拟重启→恢复→平仓→无 JSON 孤儿仓位检测
5. **熔断**：开仓+挂 SL→cancel_all→全平→确认清零

### 步骤 5：部署 Vultr + 测试网跑全链路

```bash
scp lab/limit_executor.py lab/unified_trader.py lab/test_full_chain.py root@100.122.227.7:/opt/auto-trading/lab/
ssh root@100.122.227.7 "cd /opt/auto-trading/lab && BITMEX_TESTNET=true python3 test_full_chain.py 2>&1"
```

### 步骤 6：输出汇总表 + 完整测试结果原样贴给顾问

---

## 关键文件

| 文件 | 操作 | Bug |
|------|------|-----|
| `lab/limit_executor.py` | 修改 | Bug 1, 3 |
| `lab/unified_trader.py` | 修改 | Bug 1调用端, 2, 4, 5, 6, 7 |
| `lab/test_full_chain.py` | 新建 | 验证 |
| `lab/strategy_runner.py` | 不改 | 无 bug |
| `lab/team_config.py` | 不改 | 无 bug |

## 验证（6 个关键点）

1. 注码链路：保证金 → 名义 → 币数量 正确？
2. position_size 全程是币数量？（不是微量 0.000001）
3. SL/TP 挂单方向和 strategy 正确？
4. Close 平仓自动取消 SL/TP？（挂单数=0）
5. 崩溃恢复后能正确平仓？
6. 熔断后零仓位零挂单？
