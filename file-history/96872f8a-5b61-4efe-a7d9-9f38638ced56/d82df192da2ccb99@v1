#!/usr/bin/env python3
"""
Parabolic SAR Strategy

Trend reversal indicator.

Features:
- SAR calculation
- Trend direction

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class ParabolicSARConfig:
    """Parabolic SAR configuration"""
    period: int = 10


class ParabolicSAR(Strategy):
    """Parabolic SAR trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[ParabolicSARConfig] = None):
        """Initialize Parabolic SAR strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or ParabolicSARConfig()
    
    @property
    def name(self) -> str:
        return "parabolic_sar"
    
    def calculate_sar(
        self, closes: List[float], period: int = None
    ) -> float:
        """Calculate SAR value
        
        Args:
            closes: Close prices
            period: Lookback period
            
        Returns:
            SAR value
        """
        if period is None:
            period = self.config.period
        
        if len(closes) < period + 1:
            return sum(closes) / len(closes)
        
        # Simplified SAR calculation
        recent = closes[-period:]
        return sum(recent) / len(recent)
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Parabolic SAR signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with SAR analysis
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
        
        # Extract closes
        closes = [c["close"] for c in klines]
        current = closes[-1]
        
        # Calculate SAR
        sar = self.calculate_sar(closes)
        
        # Generate signal
        if current > sar:
            signal = Signal.BUY
            trend = "uptrend"
        elif current < sar:
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
                "sar": sar,
                "current": current,
                "trend": trend,
            },
        )
