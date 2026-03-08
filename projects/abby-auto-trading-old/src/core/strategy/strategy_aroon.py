#!/usr/bin/env python3
"""
Aroon Strategy - Aroon Indicator

Trend reversal detection using true Aroon methodology.

Features:
- Aroon Up/Down calculation based on price highs/lows
- Crosses indicate trend changes

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class AroonConfig:
    """Aroon strategy configuration"""
    period: int = 25  # Aroon lookback period


class Aroon(Strategy):
    """Aroon trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[AroonConfig] = None):
        """Initialize Aroon strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or AroonConfig()
    
    @property
    def name(self) -> str:
        return "aroon"
    
    def calculate_aroon(self, closes: List[float]) -> tuple:
        """Calculate true Aroon indicator
        
        Args:
            closes: Close prices
            
        Returns:
            Tuple of (aroon_up, aroon_down, aroon_oscillator)
        """
        period = self.config.period
        
        if len(closes) < period:
            return 0.0, 0.0, 0.0
        
        # Get the last 'period' closes
        lookback = closes[-period:]
        
        # Find highest and lowest in the lookback period
        highest = max(lookback)
        lowest = min(lookback)
        
        # Find position of highest and lowest (0 = most recent)
        # days_since_high = how many bars ago the high occurred
        days_since_high = period - 1 - lookback[::-1].index(highest)
        days_since_low = period - 1 - lookback[::-1].index(lowest)
        
        # Aroon Up = ((period - days_since_high) / period) * 100
        # 100 when high was just made, 0 when high was period bars ago
        aroon_up = ((period - days_since_high) / period) * 100
        
        # Aroon Down = ((period - days_since_low) / period) * 100
        aroon_down = ((period - days_since_low) / period) * 100
        
        # Aroon Oscillator = Aroon Up - Aroon Down
        aroon_osc = aroon_up - aroon_down
        
        return aroon_up, aroon_down, aroon_osc
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Aroon trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with Aroon analysis
        """
        # Validate klines
        min_required = self.config.period
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
        
        # Calculate true Aroon indicator
        aroon_up, aroon_down, aroon_osc = self.calculate_aroon(closes)
        
        # Generate signal based on Aroon crossover
        # Aroon Up > Aroon Down = bullish (BUY)
        # Aroon Down > Aroon Up = bearish (SELL)
        
        if aroon_up > aroon_down:
            signal = Signal.BUY
            trend = "uptrend"
            confidence = min(aroon_osc / 100, 1.0)  # Higher oscillator = more confident
        elif aroon_down > aroon_up:
            signal = Signal.SELL
            trend = "downtrend"
            confidence = min(aroon_osc / -100, 1.0)
        else:
            signal = Signal.HOLD
            trend = "consolidation"
            confidence = 0.0
        
        return TradingSignal(
            signal=signal,
            confidence=abs(confidence) if confidence else 0.0,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "aroon_up": aroon_up,
                "aroon_down": aroon_down,
                "aroon_oscillator": aroon_osc,
                "trend": trend,
            },
        )
