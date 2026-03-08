#!/usr/bin/env python3
"""
Donchian Strategy

Breakout strategy.

Features:
- High/low channel breakout
- New high/new low signals

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class DonchianConfig:
    """Donchian configuration"""
    period: int = 20


class Donchian(Strategy):
    """Donchian trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[DonchianConfig] = None):
        """Initialize Donchian strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or DonchianConfig()
    
    @property
    def name(self) -> str:
        return "donchian"
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Donchian signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with breakout analysis
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
        highs = [c["high"] for c in klines[-self.config.period :]]
        lows = [c["low"] for c in klines[-self.config.period :]]
        current = klines[-1]["close"]
        
        # Donchian channels
        highest_high = max(highs[:-1]) if len(highs) > 1 else max(highs)
        lowest_low = min(lows[:-1]) if len(lows) > 1 else min(lows)
        
        # Generate signal
        if current > highest_high:
            signal = Signal.BUY
            trend = "breakout_up"
        elif current < lowest_low:
            signal = Signal.SELL
            trend = "breakout_down"
        else:
            signal = Signal.HOLD
            trend = "consolidation"
        
        return TradingSignal(
            signal=signal,
            confidence=0.7,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "highest_high": highest_high,
                "lowest_low": lowest_low,
                "current": current,
                "trend": trend,
            },
        )
