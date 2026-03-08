# 链上/宏观指标研究（2026-02-26）

## 用户原话
> 市面上其实还有一些指标是直指目前整个币圈市场的，比如有一个叫什么arh999？还有一些大指标，比如链上信息，整个市场的稳定币一直在增加代表市场越来越好，虽然币价下跌，但是很大可能会反弹。还有交易所的流入流出，如果很多币流入，代表随时会砸盘，流出代表巨鲸或机构已经抄好底了，坐等币价上涨。
> 反正我们现在有数据，我们就可以用这些真实的数据来验证我们的指标，是不是有效
> 或者我们可以做指标库，有需要的时候就调用指标库的数据来验证

## Tier 1：自己能算，不需要外部 API

| 指标 | 算法 | 阈值 | 数据需求 |
|------|------|------|----------|
| **AHR999（九神指标）** | `(价格/200日均价) × (价格/对数增长估值)` | <0.45 抄底, 0.45-1.2 定投, >5 卖出 | BTC 日线价格（已有） |
| **Pi Cycle Top** | 111日SMA 上穿 350日SMA×2 = 周期顶部 | 交叉即信号 | BTC 日线价格（已有） |
| **Funding Rate** | HyperLiquid 直接提供 | 8h>0.1% 过热, <-0.01% 投降 | HyperLiquid API（已有） |
| **Open Interest** | HyperLiquid 直接提供 | OI涨+价涨=新钱, OI涨+价跌=做空 | HyperLiquid API（已有） |

## Tier 2：免费 API，一个请求搞定

| 指标 | API | 频率限制 | 阈值 |
|------|-----|----------|------|
| **Fear & Greed** | `api.alternative.me/fng/` 无需key | 60次/分 | 0-25极度恐惧(买), 75-100极度贪婪(卖) |
| **稳定币总量** | `stablecoins.llama.fi/stablecoins` 无需key | 无限制 | 持续增加=干火药充足=看涨 |
| **BTC Dominance** | `api.coingecko.com/api/v3/global` 无需key | 30次/分 | >60%避险, <40%山寨季 |

## Tier 3：免费但限速的链上数据

**BGeometrics**: `bitcoin-data.com/v1/` — 免费，8次/小时，15次/天

| 指标 | 端点 | 说明 | 阈值 |
|------|------|------|------|
| **MVRV Z-Score** | `/mvrv-zscore` | 最强周期指标 | <0 抄底, >7 逃顶 |
| **NUPL** | `/nupl` | 市场情绪阶段 | <0 投降(买), >0.75 狂热(卖) |
| **Puell Multiple** | `/puell-multiple` | 矿工经济 | <0.5 矿工投降(买), >4 过热(卖) |
| **Exchange Inflow** | `/exchange-inflow` | 交易所流入 | 大量流入=砸盘风险 |
| **Exchange Outflow** | `/exchange-outflow` | 交易所流出 | 大量流出=巨鲸囤货 |
| **Exchange Netflow** | `/exchange-netflow` | 净流量 | 负=看涨, 正=看跌 |

## Tier 4：付费（暂不需要）
- Glassnode Pro $79/月
- CryptoQuant API 付费
- Stock-to-Flow: **已被证伪，不用**

## 建议打分系统
```
Market Score = 加权平均:
  AHR999 (20%) + MVRV (20%) + NUPL (15%) +
  Fear&Greed (10%) + Funding (10%) +
  稳定币趋势 (10%) + Puell (10%) + BTC.D (5%)

0.0-0.3 = 深熊（抄底区）
0.3-0.5 = 早期复苏
0.5-0.7 = 牛市
0.7-0.9 = 牛市后期（止盈区）
0.9-1.0 = 狂热（逃顶）
```

## 关键 API 端点
```python
# Fear & Greed（免费无key）
requests.get("https://api.alternative.me/fng/?limit=30")

# 稳定币（免费无key）
requests.get("https://stablecoins.llama.fi/stablecoins")

# BTC Dominance（免费无key）
requests.get("https://api.coingecko.com/api/v3/global")

# HyperLiquid Funding+OI（免费无key）
requests.post("https://api.hyperliquid.xyz/info", json={"type": "metaAndAssetCtxs"})

# BGeometrics 链上（免费无key，8次/小时）
requests.get("https://bitcoin-data.com/v1/mvrv-zscore")
requests.get("https://bitcoin-data.com/v1/nupl")
requests.get("https://bitcoin-data.com/v1/puell-multiple")
requests.get("https://bitcoin-data.com/v1/exchange-netflow")
```

## 实现计划：指标库架构
用户想法：做一个指标库，需要时调用来验证策略有效性

```
src/indicators/
  __init__.py
  base.py          — IndicatorBase 基类
  ahr999.py        — 自算，用已有BTC价格
  pi_cycle.py      — 自算，用已有BTC价格
  fear_greed.py    — alternative.me API
  stablecoin.py    — DefiLlama API
  btc_dominance.py — CoinGecko API
  funding.py       — HyperLiquid API
  open_interest.py — HyperLiquid API
  onchain.py       — BGeometrics API (MVRV/NUPL/Puell/Exchange flow)
  composite.py     — 综合打分系统
```

每个指标类：
- `fetch()` → 获取最新数据
- `score()` → 归一化到 0-1（0=极度看跌, 1=极度看涨）
- `signal()` → "strong_buy" / "buy" / "neutral" / "sell" / "strong_sell"
- 本地缓存（链上数据日更，不需要频繁请求）
