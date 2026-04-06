# BitMEX API Documentation - Complete Reference

> Compiled from docs.bitmex.com API Explorer + Swagger spec + Schema API
> Date: 2026-03-23

---

## Table of Contents
1. [ORDER V1](#order-v1)
2. [ORDER V2](#order-v2)
3. [POSITION & MARGIN](#position--margin)
4. [Response Schema Definitions](#response-schema-definitions)

---

# ORDER V1

## 1. GET /api/v1/order — Get Orders

**Category:** Order V1
**HTTP Method:** GET
**Path:** `/api/v1/order`

**Description:** Returns order history. To retrieve only open orders, send `{"open": true}` in the filter parameter. See the FIX specification for field definitions.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `symbol` | string | Optional | query | Instrument symbol. e.g. 'XBTUSD' |
| `filter` | string (JSON) | Optional | query | Generic table filter. e.g. `{"open": true}` |
| `columns` | string (JSON) | Optional | query | Column names to fetch. Omit to get all columns. |
| `count` | int32 | Optional (default: 100) | query | Number of results to fetch. Max 500. |
| `start` | int32 | Optional (default: 0) | query | Starting point for results. |
| `reverse` | boolean | Optional (default: false) | query | If true, sort results newest first. |
| `startTime` | datetime | Optional | query | Starting date filter for results. |
| `endTime` | datetime | Optional | query | Ending date filter for results. |

### Response
- **200:** Array of Order objects
- **400:** Parameter error
- **401:** Unauthorized
- **403:** Access denied
- **404:** Not found

---

## 2. PUT /api/v1/order — Amend Order

**Category:** Order V1
**HTTP Method:** PUT
**Path:** `/api/v1/order`

**Description:** Amend the quantity or price of an open order. Send `orderID` or `origClOrdID` to identify the order to modify. Both quantity and price can be amended. Only one `qty` field can be used to amend.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `orderID` | string | Optional* | formData | Order ID. *Either orderID or origClOrdID required. |
| `origClOrdID` | string | Optional* | formData | Original client order ID. *Either orderID or origClOrdID required. |
| `clOrdID` | string | Optional | formData | New client order ID (optional). |
| `orderQty` | int32 | Optional | formData | New order quantity. Only one qty field can be used. |
| `leavesQty` | int32 | Optional | formData | Remaining quantity desired. Useful for adjusting position delta regardless of fills. |
| `price` | double | Optional | formData | New limit price. |
| `stopPx` | double | Optional | formData | New stop price. |

### Notes
- A `leavesQty` can be used to make a 'Filled' order live again, if received within 60 seconds of the fill.
- `leavesQty` is useful when you want to adjust your position's delta by a specific amount, regardless of how much has already filled.

### Response
- **200:** Single Order object
- **400:** Parameter error
- **401:** Unauthorized
- **403:** Access denied
- **404:** Not found

---

## 3. DELETE /api/v1/order — Cancel Order(s)

**Category:** Order V1
**HTTP Method:** DELETE
**Path:** `/api/v1/order`

**Description:** Cancel order(s). Send multiple order IDs to cancel in bulk. Either `orderID` or `clOrdID` must be provided.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `orderID` | string (JSON) | Optional* | formData | Order ID(s) to cancel. Can be a JSON array for bulk cancellation. *Either orderID or clOrdID required. |
| `clOrdID` | string (JSON) | Optional* | formData | Client order ID(s) to cancel. Can be a JSON array. *Either orderID or clOrdID required. |
| `text` | string | Optional | formData | Optional cancellation annotation. e.g. 'Spread Exceeded' |

### Response
- **200:** Array of Order objects
- **400:** Parameter error
- **401:** Unauthorized
- **403:** Access denied
- **404:** Not found

---

## 4. DELETE /api/v1/order/all — Cancel All Orders

**Category:** Order V1
**HTTP Method:** DELETE
**Path:** `/api/v1/order/all`

**Description:** Cancel all of your orders.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `targetAccountIds` | string (JSON) | Optional | formData | AccountIds to cancel all orders for, must be a paired account with main user. Also accepts wildcard `[*]`, which cancels all orders for all accounts the authenticated user has order write permissions for. |
| `symbol` | string | Optional | formData | Optional symbol. If provided, only cancels orders for that symbol. |
| `filter` | string (JSON) | Optional | formData | Optional filter for cancellation. Use to only cancel some orders, e.g. `{"side": "Buy"}`. |
| `text` | string | Optional | formData | Optional cancellation annotation. e.g. 'Spread Exceeded' |

### Response
- **200:** Array of Order objects
- **400:** Parameter error
- **401:** Unauthorized
- **403:** Access denied
- **404:** Not found

---

## 5. POST /api/v1/order/cancelAllAfter — Cancel All After (Dead Man's Switch)

**Category:** Order V1
**HTTP Method:** POST
**Path:** `/api/v1/order/cancelAllAfter`

**Description:** Automatically cancel all orders after a specified timeout. Useful as a dead-man's switch to ensure orders are canceled in case of an outage. If called repeatedly, the existing timeout is replaced by the new one.

**Usage Pattern:** Call this route at 15-second intervals with a timeout of 60000 (60 seconds). If this route is not called within 60 seconds, all orders will be automatically canceled.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `timeout` | double | **Required** | formData | Timeout in milliseconds. Set to 0 to cancel this timer. |

### Notes
- Also available via WebSocket API as a "Dead Man's Switch" feature.
- Each new call replaces the previous timeout setting.

### Response
- **200:** Success
- **400:** Parameter error
- **401:** Unauthorized
- **403:** Access denied
- **404:** Not found

---

# ORDER V2

> V2 endpoints mirror V1 functionality but use the `/api/v2/` base path. The V2 endpoints have the same parameter structure as V1 unless noted otherwise.

## 6. POST /api/v2/order — Create New Order

**Category:** Order V2
**HTTP Method:** POST
**Path:** `/api/v2/order`

**Description:** Place a new order. All orders require a `symbol`. Other fields are generally optional. See the FIX specification for field definitions.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `symbol` | string | **Required** | formData | Instrument symbol. e.g. 'XBTUSD'. |
| `strategy` | string | Optional | formData | Order strategy. e.g. 'OneWay', 'Long', 'Short'. |
| `side` | string | Optional | formData | Order side. Valid: Buy, Sell. Defaults to 'Buy' unless `orderQty` is negative. |
| `simpleOrderQty` | double | Optional | formData | Deprecated since 2018/10/26. |
| `orderQty` | int32 | Optional | formData | Order quantity in units of the instrument (contracts; for spot: base currency in minor units, e.g. XBt for XBT). |
| `price` | double | Optional | formData | Limit price for 'Limit', 'StopLimit', and 'LimitIfTouched' orders. |
| `displayQty` | int32 | Optional | formData | Quantity to display in the book. Use 0 for a fully hidden order. |
| `stopPx` | double | Optional | formData | Trigger price for 'Stop', 'StopLimit', 'MarketIfTouched', 'LimitIfTouched' orders. Use price below current for stop-sell and buy-if-touched. Use `execInst` of 'MarkPrice' or 'LastPrice' to define triggering price. |
| `clOrdID` | string | Optional | formData | Client Order ID (max 36 chars). Comes back on the order and any related executions. |
| `clOrdLinkID` | string | Optional | formData | Client Order Link ID for contingent orders. |
| `pegOffsetValue` | double | Optional | formData | Trailing offset from current price for stop/touch orders; offset from peg price for 'Pegged' orders. Use negative for stop-sell/buy-if-touched. |
| `pegPriceType` | string | Optional | formData | Peg price type. Valid: MarketPeg, PrimaryPeg, TrailingStopPeg. |
| `ordType` | string | Optional (default: Limit) | formData | Order type. Valid: Market, Limit, Stop, StopLimit, MarketIfTouched, LimitIfTouched, Pegged. Defaults to 'Limit' when `price` specified, 'Stop' when `stopPx` specified, 'StopLimit' when both specified. |
| `timeInForce` | string | Optional | formData | Time in force. Valid: Day, GoodTillCancel, ImmediateOrCancel, FillOrKill. Defaults to 'GoodTillCancel' for Limit, StopLimit, LimitIfTouched. |
| `execInst` | string | Optional | formData | Execution instructions (comma-separated). Valid: ParticipateDoNotInitiate, AllOrNone, MarkPrice, IndexPrice, LastPrice, Close, ReduceOnly, Fixed, LastWithinMark. See details below. |
| `contingencyType` | string | Optional | formData | Contingency type for `clOrdLinkID`. Valid: OneCancelsTheOther, OneTriggersTheOther. |
| `text` | string | Optional | formData | Order annotation. e.g. 'Take profit'. |
| `maxSlippagePct` | double | Optional | formData | Maximum slippage percentage for the order. |

### Order Types Detail

| ordType | Required Fields | Behavior |
|---------|----------------|----------|
| **Limit** (default) | `orderQty`, `price` | Standard limit order. |
| **Market** | `orderQty` | Executes until filled or bankruptcy price reached, then cancels remaining. |
| **Stop** (Stop Loss) | `orderQty`, `stopPx` | Market order triggered when `stopPx` reached. Sell: triggers when price falls below stopPx. Buy: triggers when price rises above stopPx. |
| **StopLimit** | `orderQty`, `price`, `stopPx` | Like Stop but enters a limit order instead of market order at trigger. |
| **MarketIfTouched** | `orderQty`, `stopPx` | Opposite trigger direction from Stop. Useful for take-profit. |
| **LimitIfTouched** | `orderQty`, `price`, `stopPx` | Take-profit limit order variant. |
| **Pegged** | `orderQty`, `pegPriceType`, `pegOffsetValue` | Limit price set relative to market using peg type + offset. |

### Execution Instructions Detail

| execInst | Description |
|----------|-------------|
| `ParticipateDoNotInitiate` | Post-only order. Cancels if it would immediately execute (take liquidity). |
| `AllOrNone` | Requires `displayQty` = 0. Entire order must fill or nothing. |
| `MarkPrice` | Use mark price for triggering stop/touch orders. |
| `IndexPrice` | Use index price for triggering. |
| `LastPrice` | Use last trade price for triggering. |
| `Close` | Reduces position only. Cancels other conflicting close orders so margin is freed for this order. Ensures stop executions. |
| `ReduceOnly` | Order can only reduce position, never increase. Not applicable to spot. |
| `Fixed` | Required for pegged orders. Price set at submission doesn't change with reference price. |
| `LastWithinMark` | Valid for Stop/StopLimit with LastPrice. Restricts triggers to be within mark price bounds. Not applicable to spot. |

### Advanced Features

**Trailing Stop Pegged Orders:** Prices update once per second if underlying prices move over 0.1%.

**Linked Orders (OCO/OTO):** Use `clOrdLinkID` + `contingencyType`:
- `OneCancelsTheOther` (OCO): One fill cancels the other linked orders.
- `OneTriggersTheOther` (OTO): One fill activates the other linked orders.

### Notes
- Stop loss orders do not consume margin before trigger. Ensure sufficient available margin when triggered.
- `Close` stop orders do not require `orderQty`.
- `clOrdID` max 36 characters. Can be used to amend/cancel via `origClOrdID`.

### Response
- **200:** Single Order object
- **400:** Parameter error
- **401:** Unauthorized
- **403:** Access denied
- **404:** Not found

---

## 7. PUT /api/v2/order — Amend Order

**Category:** Order V2
**HTTP Method:** PUT
**Path:** `/api/v2/order`

**Description:** Amend the quantity or price of an open order. Send `orderID` or `origClOrdID` to identify the order. Both order quantity and price can be amended. Only one `qty` field can be used.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `orderID` | string | Optional* | formData | Order ID. *Either orderID or origClOrdID required. |
| `origClOrdID` | string | Optional* | formData | Original client order ID. *Either orderID or origClOrdID required. |
| `clOrdID` | string | Optional | formData | New client order ID. |
| `orderQty` | int32 | Optional | formData | New order quantity. Only one qty field can be used. |
| `leavesQty` | int32 | Optional | formData | Remaining open quantity desired. |
| `price` | double | Optional | formData | New limit price. |
| `stopPx` | double | Optional | formData | New stop/trigger price. |

### Notes
- A `leavesQty` can be used to make a 'Filled' order live again, if received within 60 seconds of the fill.
- Useful for adjusting position delta by a specific amount regardless of partial fills.

### Response
- **200:** Single Order object
- **400-404:** Same as V1

---

## 8. DELETE /api/v2/order — Cancel Order(s)

**Category:** Order V2
**HTTP Method:** DELETE
**Path:** `/api/v2/order`

**Description:** Cancel order(s). Either `orderID` or `clOrdID` must be provided.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `orderID` | string (JSON) | Optional* | formData | Order ID(s). *Either orderID or clOrdID required. |
| `clOrdID` | string (JSON) | Optional* | formData | Client order ID(s). *Either orderID or clOrdID required. |
| `text` | string | Optional | formData | Cancellation annotation. |

### Response
- **200:** Array of Order objects
- **400-404:** Same as V1

---

## 9. DELETE /api/v2/order/all — Cancel All Orders

**Category:** Order V2
**HTTP Method:** DELETE
**Path:** `/api/v2/order/all`

**Description:** Cancel all of your orders.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `targetAccountIds` | string (JSON) | Optional | formData | AccountIds to cancel for (paired accounts). Accepts wildcard `[*]`. |
| `symbol` | string | Optional | formData | Optional symbol filter. |
| `filter` | string (JSON) | Optional | formData | Optional filter. e.g. `{"side": "Buy"}`. |
| `text` | string | Optional | formData | Cancellation annotation. |

### Response
- **200:** Array of Order objects
- **400-404:** Same as V1

---

## 10. POST /api/v2/order/bulkorder — Create Conditional Orders (Bulk)

**Category:** Order V2
**HTTP Method:** POST
**Path:** `/api/v2/order/bulkorder`

**Description:** Create contingent (conditional) orders in bulk. **This API is only available to clients with bespoke arrangement.** Contact your relationship manager to use it. Non-conditional order submissions are rejected.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `orders` | string (JSON array) | **Required** | formData | Array of order objects. Each order follows the same schema as POST /api/v2/order, but must be conditional orders. |

### Notes
- **Restricted access**: Only available to clients with custom arrangements.
- Standard (non-conditional) orders will be rejected through this endpoint.

### Response
- **200:** Array of Order objects
- **400-404:** Same as V1

---

## 11. POST /api/v2/order/cancelAllAfter — Cancel All After (Dead Man's Switch)

**Category:** Order V2
**HTTP Method:** POST
**Path:** `/api/v2/order/cancelAllAfter`

**Description:** Dead-man's switch. Automatically cancels all orders if not called within the specified timeout. Each call replaces the previous timeout.

**Usage Pattern:** Call every 15 seconds with timeout=60000 (60s). If not called within 60s, all orders auto-cancel.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `timeout` | double | **Required** | formData | Timeout in milliseconds. Set to 0 to cancel this timer. |

### Notes
- Also available via WebSocket API.
- Each new call replaces the previous timeout.

### Response
- **200:** Success
- **400-404:** Same as V1

---

# POSITION & MARGIN

## 12. GET /api/v1/position — Get Positions

**Category:** Position & Margin
**HTTP Method:** GET
**Path:** `/api/v1/position`

**Description:** Retrieve position information. Fields `account`, `symbol`, and `currency` are unique per position (composite key). Spot trading symbols return a subset of position fields, primarily unsettled order summaries.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `filter` | string (JSON) | Optional | query | Table filter. e.g. `{"symbol": "XBTUSD"}` |
| `columns` | string (JSON) | Optional | query | Columns to fetch. Omit for all. |
| `count` | int32 | Optional | query | Number of rows to fetch. |

### Response
- **200:** Array of Position objects (see schema below)
- **400-404:** Standard errors

---

## 13. POST /api/v1/position/isolate — Enable Isolated/Cross Margin

**Category:** Position & Margin
**HTTP Method:** POST
**Path:** `/api/v1/position/isolate`

**Description:** Enable isolated margin or cross margin per-position. Toggle isolated (fixed) margin settings on individual positions.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `symbol` | string | **Required** | formData | Position symbol to isolate. |
| `enabled` | boolean | Optional (default: true) | formData | True for isolated margin, false for cross margin. |

### Response
- **200:** Single Position object
- **400-404:** Standard errors

---

## 14. POST /api/v1/position/riskLimit — Update Risk Limit

**Category:** Position & Margin
**HTTP Method:** POST
**Path:** `/api/v1/position/riskLimit`

**Description:** Update your risk limit. Risk Limits constrain the position size you can trade at various margin levels. Larger positions require increased margin allocation.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `symbol` | string | **Required** | formData | Symbol of position to update risk limit on. |
| `riskLimit` | int64 | **Required** | formData | New Risk Limit, in Satoshis. |
| `targetAccountId` | double | Optional | formData | AccountId for the position (must be a paired account with main user). |

### Response
- **200:** Single Position object
- **400-404:** Standard errors

---

## 15. POST /api/v1/position/transferMargin — Transfer Margin

**Category:** Position & Margin
**HTTP Method:** POST
**Path:** `/api/v1/position/transferMargin`

**Description:** Transfer equity in or out of a position. When margin is isolated on a position, use this to add or remove margin. Cannot remove margin below the initial margin level.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `symbol` | string | **Required** | formData | Symbol of position to transfer margin for. |
| `amount` | int64 | **Required** | formData | Amount to transfer, in Satoshis. May be negative (to remove margin). |
| `targetAccountId` | double | Optional | formData | AccountId for the position (must be a paired account with main user). |

### Notes
- Cannot withdraw margin below the initial margin threshold.
- Only works for positions in isolated margin mode.

### Response
- **200:** Single Position object
- **400-404:** Standard errors

---

## 16. POST /api/v1/position/leverage — Choose Leverage (Isolated)

**Category:** Position & Margin
**HTTP Method:** POST
**Path:** `/api/v1/position/leverage`

**Description:** Choose leverage for a position. Selecting isolated leverage automatically enables isolated margin.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `symbol` | string | **Required** | formData | Symbol of position to adjust. |
| `leverage` | double | **Required** | formData | Leverage value. Send 0.01-100 for isolated margin with fixed leverage. Send 0 to enable cross margin. |
| `targetAccountId` | double | Optional | formData | AccountId for the position (must be a paired account with main user). |

### Notes
- Setting leverage automatically enables isolated margin.
- Sending leverage = 0 switches to cross margin.

### Response
- **200:** Single Position object
- **400-404:** Standard errors

---

## 17. POST /api/v1/position/crossLeverage — Choose Leverage (Cross)

**Category:** Position & Margin
**HTTP Method:** POST
**Path:** `/api/v1/position/crossLeverage`

**Description:** Set leverage on a cross-margin position. Users can choose leverage while remaining in cross margin mode.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `symbol` | string | **Required** | formData | Symbol of position to adjust. |
| `leverage` | double | **Required** | formData | Leverage value. Send 0.01-100 for isolated margin with fixed leverage. Send 0 for cross margin. |
| `targetAccountId` | double | Optional | formData | AccountId for the position (must be a paired account with main user). |

### Notes
- Unlike `/position/leverage`, this endpoint is specifically for adjusting leverage on cross-margin positions without switching margin mode.

### Response
- **200:** Single Position object
- **400-404:** Standard errors

---

## 18. POST /api/v1/user/marginingMode — Set Margining Mode

**Category:** Position & Margin
**HTTP Method:** POST
**Path:** `/api/v1/user/marginingMode`

**Description:** Switch margining mode between single-asset margining and multi-asset margining.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `mode` | string | **Required** | formData | Margining mode. Expected values: single-asset or multi-asset margining mode identifier. |

### Notes
- This is an account-level setting, not per-position.
- Single-asset margining: each currency's margin is isolated.
- Multi-asset margining: all assets can contribute to margin.
- The Swagger spec does not list this endpoint; parameter name inferred from functionality.

### Response
- **200:** Success
- **400-404:** Standard errors

---

## 19. GET /api/v1/user/marginingMode — Get Margining Mode

**Category:** Position & Margin
**HTTP Method:** GET
**Path:** `/api/v1/user/marginingMode`

**Description:** Retrieve the current margining mode setting for the user account.

### Parameters

None. Simple GET request.

### Response
- **200:** Current margining mode setting
- **400-404:** Standard errors

---

## 20. GET /api/v1/user/margin — Get Margin(s)

**Category:** Position & Margin
**HTTP Method:** GET
**Path:** `/api/v1/user/margin`

**Description:** Retrieve margin information for all assets for the logged-in account and its subaccounts. Each entry contains data about the margin amount in the system, order and position requirements for a specific currency.

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `currency` | string | Optional | query | Currency filter. e.g. 'XBt', 'USDt'. |

### Notes
- Can return either a single object or a list, depending on whether multiple assets and/or accounts are requested.
- Not present in the public Swagger spec (may be a newer or restricted endpoint).

### Response
- **200:** Single Margin object or Array of Margin objects (see schema below)
- **400-404:** Standard errors

---

## 21. POST /api/v1/user/positionMode — Choose Position Mode

**Category:** Position & Margin
**HTTP Method:** POST
**Path:** `/api/v1/user/positionMode`

**Description:** Switch between one-way position mode (unidirectional) and multi-way position mode (bidirectional / hedge mode).

### Parameters

| Name | Type | Required | Location | Description |
|------|------|----------|----------|-------------|
| `mode` | string | **Required** | formData | Position mode. Expected values correspond to one-way or multi-way (hedge) mode. |

### Notes
- One-way mode: single position per symbol (net position).
- Multi-way (hedge) mode: separate long and short positions per symbol.
- This is an account-level setting.
- The Swagger spec does not list this endpoint; parameter name inferred from functionality.

### Response
- **200:** Success
- **400-404:** Standard errors

---

# RESPONSE SCHEMA DEFINITIONS

## Order Object

| Field | Type | Description |
|-------|------|-------------|
| `orderID` | guid | Unique order identifier (primary key) |
| `clOrdID` | string | Client-assigned order ID |
| `clOrdLinkID` | string | Client order link ID for contingent orders |
| `account` | long | Account number |
| `symbol` | string | Instrument symbol |
| `side` | string | Buy or Sell |
| `orderQty` | long | Order quantity |
| `price` | float | Limit price |
| `stopPx` | float | Trigger/stop price |
| `pegOffsetValue` | float | Peg offset value |
| `pegPriceType` | string | Peg price type |
| `currency` | string | Currency |
| `settlCurrency` | string | Settlement currency |
| `ordType` | string | Order type (Market, Limit, Stop, etc.) |
| `timeInForce` | string | Time in force |
| `execInst` | string | Execution instructions |
| `contingencyType` | string | Contingency type |
| `ordStatus` | string | Order status |
| `triggered` | string | Trigger status |
| `workingIndicator` | boolean | Whether order is working in the book |
| `ordRejReason` | string | Rejection reason |
| `leavesQty` | long | Remaining open quantity |
| `cumQty` | long | Cumulative filled quantity |
| `avgPx` | float | Average fill price |
| `displayQty` | long | Displayed quantity |
| `text` | string | Order annotation text |
| `transactTime` | timestamp | Transaction time |
| `timestamp` | timestamp | Last update timestamp |
| `error` | string | Error message (if any) |
| `strategy` | string | Order strategy |
| `destination` | string | Destination |
| `pool` | string | Pool |
| `maxSlippagePct` | float | Maximum slippage percentage |
| `algoOrderDetails` | object | Algorithm order details |

---

## Position Object

| Field | Type | Description |
|-------|------|-------------|
| `account` | long | Account number (key) |
| `symbol` | string | Symbol (key) |
| `strategy` | string | Strategy (key) |
| `currency` | string | Currency |
| `underlying` | string | Underlying asset |
| `quoteCurrency` | string | Quote currency |
| `commission` | float | Commission rate |
| `initMarginReq` | float | Initial margin requirement |
| `maintMarginReq` | float | Maintenance margin requirement |
| `riskLimit` | long | Risk limit |
| `leverage` | float | Current leverage |
| `crossMargin` | boolean | Whether cross margin is enabled |
| `deleveragePercentile` | float | Auto-deleverage percentile |
| `rebalancedPnl` | long | Rebalanced PnL |
| `prevRealisedPnl` | long | Previous realised PnL |
| `prevUnrealisedPnl` | long | Previous unrealised PnL |
| `openingQty` | long | Opening quantity |
| `openOrderBuyQty` | long | Open buy order quantity |
| `openOrderBuyCost` | long | Open buy order cost |
| `openOrderBuyPremium` | long | Open buy order premium |
| `openOrderSellQty` | long | Open sell order quantity |
| `openOrderSellCost` | long | Open sell order cost |
| `openOrderSellPremium` | long | Open sell order premium |
| `currentQty` | long | Current position quantity |
| `currentCost` | long | Current cost basis |
| `currentComm` | long | Current commission |
| `realisedCost` | long | Realised cost |
| `unrealisedCost` | long | Unrealised cost |
| `grossOpenPremium` | long | Gross open premium |
| `isOpen` | boolean | Whether position is open |
| `markPrice` | float | Mark price |
| `markValue` | long | Mark value |
| `riskValue` | long | Risk value |
| `homeNotional` | float | Home notional value |
| `foreignNotional` | float | Foreign notional value |
| `posState` | string | Position state |
| `posCost` | long | Position cost |
| `posCross` | long | Position cross margin |
| `posComm` | long | Position commission |
| `posLoss` | long | Position loss |
| `posMargin` | long | Position margin |
| `posMaint` | long | Position maintenance margin |
| `initMargin` | long | Initial margin |
| `maintMargin` | long | Maintenance margin |
| `realisedPnl` | long | Realised PnL |
| `unrealisedPnl` | long | Unrealised PnL |
| `unrealisedPnlPcnt` | float | Unrealised PnL percentage |
| `unrealisedRoePcnt` | float | Unrealised ROE percentage |
| `avgCostPrice` | float | Average cost price |
| `avgEntryPrice` | float | Average entry price |
| `breakEvenPrice` | float | Break-even price |
| `marginCallPrice` | float | Margin call price |
| `liquidationPrice` | float | Liquidation price |
| `bankruptPrice` | float | Bankruptcy price |
| `timestamp` | timestamp | Last update timestamp |

---

## Margin Object

| Field | Type | Description |
|-------|------|-------------|
| `account` | long | Account number (key) |
| `currency` | string | Currency (key) |
| `riskLimit` | long | Risk limit |
| `state` | string | Margin state |
| `amount` | long | Total amount in the system |
| `prevRealisedPnl` | long | Previous realised PnL |
| `grossComm` | long | Gross commission |
| `grossOpenCost` | long | Gross open cost |
| `grossOpenPremium` | long | Gross open premium |
| `grossExecCost` | long | Gross execution cost |
| `grossMarkValue` | long | Gross mark value |
| `riskValue` | long | Risk value |
| `initMargin` | long | Initial margin required |
| `maintMargin` | long | Maintenance margin required |
| `targetExcessMargin` | long | Target excess margin |
| `realisedPnl` | long | Realised PnL |
| `unrealisedPnl` | long | Unrealised PnL |
| `walletBalance` | long | Wallet balance |
| `marginBalance` | long | Margin balance (wallet + unrealised PnL) |
| `marginLeverage` | float | Margin leverage |
| `marginUsedPcnt` | float | Margin used percentage |
| `excessMargin` | long | Excess margin |
| `availableMargin` | long | Available margin for new orders |
| `withdrawableMargin` | long | Withdrawable margin |
| `systemWithdrawableMargin` | long | System withdrawable margin |
| `makerFeeDiscount` | float | Maker fee discount |
| `takerFeeDiscount` | float | Taker fee discount |
| `timestamp` | timestamp | Last update timestamp |
| `foreignMarginBalance` | long | Foreign margin balance |
| `foreignRequirement` | long | Foreign margin requirement |

---

## Common HTTP Response Codes (All Endpoints)

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Parameter error / Bad request |
| 401 | Unauthorized (invalid/missing API key) |
| 403 | Access denied (insufficient permissions) |
| 404 | Not found |

---

## Authentication Notes

All endpoints require API key authentication via:
- `api-expires` header: Request expiry timestamp
- `api-key` header: Your API key
- `api-signature` header: HMAC signature of the request

---

## V1 vs V2 Differences

The V2 endpoints (`/api/v2/order/*`) are newer versions of the V1 order endpoints. Based on documentation:
- V2 endpoints have the same parameter structure as V1
- V2 includes the additional `POST /api/v2/order/bulkorder` endpoint for conditional/contingent orders (restricted access)
- V1 has a `POST /api/v1/order` (create order) endpoint not listed in V2 docs separately but the V2 `POST /api/v2/order` serves the same purpose
- V1 includes `POST /api/v1/order/bulk` for general bulk orders (not in the requested URL list but exists in the API)

The V1 POST /api/v1/order endpoint parameters are identical to the V2 POST /api/v2/order parameters listed above (symbol, strategy, side, orderQty, price, displayQty, stopPx, clOrdID, clOrdLinkID, pegOffsetValue, pegPriceType, ordType, timeInForce, execInst, contingencyType, text, maxSlippagePct).
