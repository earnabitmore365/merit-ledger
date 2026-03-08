#!/usr/bin/env python3
"""
Advanced Kline Strategy

Advanced K-line analysis.

Features:
- Multiple indicator confirmation
- Bollinger Bands
- MACD signals

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import statistics

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class AdvancedKlineConfig:
    """Advanced Kline configuration"""
    bb_period: int = 20
    short_ma: int = 20
    long_ma: int = 50


class AdvancedKline(Strategy):
    """Advanced K-line trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[AdvancedKlineConfig] = None):
        """Initialize Advanced Kline strategy"""
        self.exchange = exchange
        self.config = config or AdvancedKlineConfig()
    
    @property
    def name(self) -> str:
        return "advanced_kline_echo"
    
    def calculate_ma(self, closes: List[float], period: int) -> float:
        """Calculate Moving Average"""
        if len(closes) < period:
            return sum(closes) / len(closes) if closes else 0.0
        return sum(closes[-period:]) / period
    
    def calculate_ema(self, data: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(data) < period:
            return sum(data) / len(data) if data else 0.0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for value in data[period:]:
            ema = (value - ema) * multiplier + ema
        return ema
    
    def calculate_bollinger_bands(self, closes: List[float]) -> Dict:
        """Calculate Bollinger Bands"""
        period = self.config.bb_period
        if len(closes) < period:
            return {"upper": closes[-1], "middle": closes[-1], "lower": closes[-1]}
        recent = closes[-period:]
        middle = sum(recent) / period
        try:
            std = statistics.stdev(recent)
        except Exception:
            std = 0.0
        return {
            "upper": middle + (std * 2),
            "middle": middle,
            "lower": middle - (std * 2),
        }
    
    def calculate_macd(self, closes: List[float]) -> Dict:
        """Calculate MACD"""
        if len(closes) < 26:
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
        ema_12 = self.calculate_ema(closes, 12)
        ema_26 = self.calculate_ema(closes, 26)
        macd_line = ema_12 - ema_26
        signal_line = self.calculate_ema(closes[-9:], 9)
        return {"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line}
    
    def get_trend(self, closes: List[float]) -> str:
        """Determine trend"""
        if len(closes) < self.config.long_ma:
            return "unknown"
        ma_short = self.calculate_ma(closes, self.config.short_ma)
        ma_long = self.calculate_ma(closes, self.config.long_ma)
        if closes[-1] > ma_short > ma_long:
            return "uptrend"
        elif closes[-1] < ma_short < ma_long:
            return "downtrend"
        return "ranging"
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Advanced Kline signal"""
        min_required = self.config.long_ma
        if not klines or len(klines) < min_required:
            return TradingSignal(signal=Signal.HOLD, confidence=0.0, coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"})
        closes = [k["close"] for k in klines]
        current = closes[-1]
        trend = self.get_trend(closes)
        bb = self.calculate_bollinger_bands(closes)
        macd = self.calculate_macd(closes)
        bb_signal = Signal.BUY if current < bb["lower"] else Signal.SELL if current > bb["upper"] else Signal.HOLD
        macd_signal = Signal.BUY if macd["histogram"] > 0 else Signal.SELL if macd["histogram"] < 0 else Signal.HOLD
        buy_count = sum(1 for s in [bb_signal, macd_signal] if s == Signal.BUY) + (1 if trend == "uptrend" else 0)
        sell_count = sum(1 for s in [bb_signal, macd_signal] if s == Signal.SELL) + (1 if trend == "downtrend" else 0)
        signal = Signal.BUY if buy_count >= 2 else Signal.SELL if sell_count >= 2 else Signal.HOLD
        return TradingSignal(signal=signal, confidence=0.6, coin=coin,
            timestamp=klines[-1]["time"],
            metadata={"trend": trend, "bb": bb, "macd": macd})
