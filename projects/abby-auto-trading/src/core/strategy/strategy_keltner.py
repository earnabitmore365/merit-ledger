#!/usr/bin/env python3
"""
Keltner Strategy

Volatility channel strategy.

Features:
- EMA center line
- ATR-based channels

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import statistics

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class KeltnerConfig:
    """Keltner configuration"""
    period: int = 20


class Keltner(Strategy):
    """Keltner Channel trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[KeltnerConfig] = None):
        """Initialize Keltner strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or KeltnerConfig()
    
    @property
    def name(self) -> str:
        return "keltner"
    
    def calculate_keltner(self, closes: List[float]) -> tuple:
        """Calculate Keltner Channel
        
        Args:
            closes: Close prices
            
        Returns:
            Tuple of (EMA, ATR, upper, lower)
        """
        if len(closes) < self.config.period:
            ema = sum(closes) / len(closes) if closes else 0.0
            atr = 0.0
        else:
            ema = sum(closes[-self.config.period :]) / self.config.period
            atr = statistics.stdev(closes[-self.config.period :]) if len(closes) > 1 else 0.0
        
        upper = ema + (2 * atr)
        lower = ema - (2 * atr)
        
        return ema, atr, upper, lower
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Keltner signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with channel analysis
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
        current = closes[-1]
        
        # Calculate Keltner
        ema, atr, upper, lower = self.calculate_keltner(closes)
        
        # Generate signal
        if current > upper:
            signal = Signal.BUY
            trend = "breakout_up"
        elif current < lower:
            signal = Signal.SELL
            trend = "breakout_down"
        else:
            signal = Signal.HOLD
            trend = "within_channel"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "ema": ema,
                "atr": atr,
                "upper": upper,
                "lower": lower,
                "current": current,
                "trend": trend,
            },
        )
