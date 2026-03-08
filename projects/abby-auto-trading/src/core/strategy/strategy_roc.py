#!/usr/bin/env python3
"""
ROC Strategy - Rate of Change

Momentum indicator.

Features:
- Rate of change calculation
- Threshold-based signals

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class ROCConfig:
    """ROC strategy configuration"""
    period: int = 10
    threshold: float = 5.0


class ROC(Strategy):
    """Rate of Change trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[ROCConfig] = None):
        """Initialize ROC strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or ROCConfig()
    
    @property
    def name(self) -> str:
        return "roc"
    
    def calculate_roc(self, closes: List[float]) -> float:
        """Calculate Rate of Change
        
        Args:
            closes: Close prices
            
        Returns:
            ROC percentage
        """
        if len(closes) < self.config.period + 1:
            return 0.0
        
        current = closes[-1]
        past = closes[-self.config.period]
        
        if past == 0:
            return 0.0
        
        return (current - past) / past * 100
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate ROC trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with ROC analysis
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
        
        # Calculate ROC
        roc = self.calculate_roc(closes)
        
        # Generate signal
        if roc > self.config.threshold:
            signal = Signal.BUY
            trend = "strong_momentum_up"
        elif roc < -self.config.threshold:
            signal = Signal.SELL
            trend = "strong_momentum_down"
        else:
            signal = Signal.HOLD
            trend = "neutral"
        
        return TradingSignal(
            signal=signal,
            confidence=min(abs(roc) / 20, 1.0),
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "roc": roc,
                "threshold": self.config.threshold,
                "trend": trend,
            },
        )
