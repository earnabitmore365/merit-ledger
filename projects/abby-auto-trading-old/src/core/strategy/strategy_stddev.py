#!/usr/bin/env python3
"""
StdDev Strategy - Standard Deviation

Volatility-based strategy.

Features:
- MA calculation
- Standard deviation bands

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import statistics

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class StdDevConfig:
    """StdDev configuration"""
    period: int = 20


class StdDev(Strategy):
    """Standard Deviation trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[StdDevConfig] = None):
        """Initialize StdDev strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or StdDevConfig()
    
    @property
    def name(self) -> str:
        return "stddev"
    
    def calculate_stddev(self, closes: List[float]) -> tuple:
        """Calculate Standard Deviation
        
        Args:
            closes: Close prices
            
        Returns:
            Tuple of (MA, StdDev, upper, lower)
        """
        period = self.config.period
        
        if len(closes) < period:
            ma = sum(closes) / len(closes) if closes else 0.0
            std = 0.0
        else:
            recent = closes[-period:]
            ma = sum(recent) / period
            std = statistics.stdev(recent) if len(recent) > 1 else 0.0
        
        upper = ma + std
        lower = ma - std
        
        return ma, std, upper, lower
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate StdDev signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with volatility analysis
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
        current = klines[-1]["close"]
        
        # Calculate
        ma, std, upper, lower = self.calculate_stddev(closes)
        
        # Generate signal
        if current > upper:
            signal = Signal.BUY
            trend = "high_volatility_up"
        elif current < lower:
            signal = Signal.SELL
            trend = "high_volatility_down"
        else:
            signal = Signal.HOLD
            trend = "normal"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "ma": ma,
                "std": std,
                "upper": upper,
                "lower": lower,
                "current": current,
                "trend": trend,
            },
        )
