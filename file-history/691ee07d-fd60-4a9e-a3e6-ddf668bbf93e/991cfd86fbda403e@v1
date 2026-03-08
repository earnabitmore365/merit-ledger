#!/usr/bin/env python3
"""
Ulcer Strategy

Drawdown-based indicator.

Features:
- High/low comparison
- Trend direction

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class UlcerConfig:
    """Ulcer configuration"""
    period: int = 20


class Ulcer(Strategy):
    """Ulcer trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[UlcerConfig] = None):
        """Initialize Ulcer strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or UlcerConfig()
    
    @property
    def name(self) -> str:
        return "ulcer"
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Ulcer signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with drawdown analysis
        """
        # Validate klines
        min_required = self.config.period + 1
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # Extract data
        closes = [c["close"] for c in klines[-self.config.period :]]
        current = klines[-1]["close"]
        previous_high = max(closes[:-1])
        previous_low = min(closes[:-1])
        
        # Generate signal
        if current > previous_high:
            signal = Signal.BUY
            trend = "new_high"
        elif current < previous_low:
            signal = Signal.SELL
            trend = "new_low"
        else:
            signal = Signal.HOLD
            trend = "consolidation"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "previous_high": previous_high,
                "previous_low": previous_low,
                "current": current,
                "trend": trend,
            },
        )
