# Strategy Registry

All available trading strategies in Abby Auto Trading Framework.

## Count

**Total Strategies**: 51

## Strategy List

### Momentum Indicators
| Strategy | Description |
|----------|-------------|
| `macd` | Moving Average Convergence Divergence |
| `rsi` | Relative Strength Index |
| `stochastic` | Stochastic Oscillator |
| `cmo` | Chande Momentum Oscillator |
| `roc` | Rate of Change |
| `williams_r` | Williams %R |
| `ultimate_oscillator` | Ultimate Oscillator |
| `trix` | Triple Exponential Average |
| `mfi_echo` | Money Flow Index |
| `stoch_rsi` | Stochastic RSI |

### Trend Indicators
| Strategy | Description |
|----------|-------------|
| `vwap` | Volume Weighted Average Price |
| `supertrend` | ATR-based Trend |
| `ma` | Moving Average |
| `ma_rsi` | MA + RSI Combo |
| `adx` | Average Directional Index |
| `aroon` | Aroon Indicator |
| `parabolic_sar` | Parabolic SAR |
| `atr` | Average True Range |
| `atr_trailing_stop` | ATR Trailing Stop |
| `ichimoku` | Ichimoku Cloud |

### Volatility Indicators
| Strategy | Description |
|----------|-------------|
| `bb_squeeze` | Bollinger Bands Squeeze |
| `bollinger_bands` | Bollinger Bands |
| `keltner` | Keltner Channel |
| `choppiness` | Choppiness Index |
| `stddev` | Standard Deviation |
| `ulcer` | Ulcer Index |

### Volume Indicators
| Strategy | Description |
|----------|-------------|
| `accumulation_distribution` | A/D Line |
| `cmf` | Chaikin Money Flow |
| `elder_ray` | Elder-Ray Index |
| `demand_index_echo` | Demand Index |
| `volume_profile` | Volume Profile |

### Price Action
| Strategy | Description |
|----------|-------------|
| `candlestick` | Candlestick Patterns |
| `advanced_kline_echo` | Advanced Kline |
| `kline` | Kline Analysis |
| `pivot_points_echo` | Pivot Points |
| `renko_echo` | Renko Charts |

### Advanced
| Strategy | Description |
|----------|-------------|
| `lstm` | LSTM Neural Network |
| `adaptive` | Adaptive Strategy |
| `smc` | Smart Money Concepts |
| `mean_reversion` | Mean Reversion |
| `momentum_echo` | Momentum Strategy |

### Other
| Strategy | Description |
|----------|-------------|
| `heikin_ashi` | Heikin Ashi |
| `donchian` | Donchian Channel |
| `proc` | Price Rate of Change |
| `vpt` | Volume Price Trend |
| `vroc` | Volume Rate of Change |
| `woodie_pivot_echo` | Woodie Pivot |

## Usage

```python
from src.core.strategy import vwap, macd, supertrend

# Create strategy
strategy = vwap.VWAPStrategy()

# Generate signal
signal = strategy.generate_signal("ETH", candles)
```

## Status

- ✅ **vwap** - Fully implemented with type hints
- ✅ **supertrend** - Fully implemented with type hints  
- ✅ **macd** - Fully implemented with type hints
- ⚠️ **others** - Templates created, need implementation

---

_Generated from echo-auto-trading project_
