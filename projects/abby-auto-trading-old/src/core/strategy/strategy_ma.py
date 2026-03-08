#!/usr/bin/env python3
"""
MA Strategy - Moving Average

Trend-following strategy.

Features:
- Simple Moving Average calculation
- Golden cross/death cross signals

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class MAConfig:
    """MA strategy configuration"""
    short_period: int = 10
    long_period: int = 25


class MA(Strategy):
    """Moving Average trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[MAConfig] = None):
        """Initialize MA strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or MAConfig()
    
    @property
    def name(self) -> str:
        return "ma"
    
    def calculate_ma(self, closes: List[float], period: int) -> float:
        """Calculate Simple Moving Average
        
        Args:
            closes: Close prices
            period: MA period
            
        Returns:
            MA value
        """
        if len(closes) < period:
            return sum(closes) / len(closes) if closes else 0.0
        
        return sum(closes[-period:]) / period
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate MA trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with MA analysis
        """
        # Validate klines
        min_required = self.config.long_period
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # Extract closes
        closes = [c["close"] for c in klines]
        
        # Calculate MAs
        ma_short = self.calculate_ma(closes, self.config.short_period)
        ma_long = self.calculate_ma(closes, self.config.long_period)
        
        # Generate signal
        if ma_short > ma_long:
            signal = Signal.BUY
            trend = "uptrend"
        elif ma_short < ma_long:
            signal = Signal.SELL
            trend = "downtrend"
        else:
            signal = Signal.HOLD
            trend = "neutral"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "ma_short": ma_short,
                "ma_long": ma_long,
                "trend": trend,
            },
        )
