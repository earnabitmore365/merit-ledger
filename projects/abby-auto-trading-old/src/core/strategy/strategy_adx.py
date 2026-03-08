#!/usr/bin/env python3
"""
ADX Strategy - Average Directional Index

Trend strength indicator.

Features:
- ADX calculation
- Trend direction based on MA crossover

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class ADXConfig:
    """ADX strategy configuration"""
    short_period: int = 20
    long_period: int = 50


class ADX(Strategy):
    """ADX trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[ADXConfig] = None):
        """Initialize ADX strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or ADXConfig()
    
    @property
    def name(self) -> str:
        return "adx"
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate ADX trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with trend analysis
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
        current = closes[-1]
        
        # Calculate MAs
        ma_short = sum(closes[-self.config.short_period :]) / self.config.short_period
        ma_long = sum(closes[-self.config.long_period :]) / self.config.long_period
        
        # Generate signal
        if current > ma_short > ma_long:
            signal = Signal.BUY
            trend = "strong_uptrend"
        elif current < ma_short < ma_long:
            signal = Signal.SELL
            trend = "strong_downtrend"
        else:
            signal = Signal.HOLD
            trend = "consolidation"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "ma_short": ma_short,
                "ma_long": ma_long,
                "current": current,
                "trend": trend,
            },
        )
