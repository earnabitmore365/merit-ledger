#!/usr/bin/env python3
"""
Awesome Oscillator Strategy

Momentum indicator.

Features:
- Dual SMA comparison
- Zero line crossover

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class AwesomeOscillatorConfig:
    """Awesome Oscillator configuration"""
    fast_period: int = 5
    slow_period: int = 34


class AwesomeOscillator(Strategy):
    """Awesome Oscillator trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[AwesomeOscillatorConfig] = None):
        """Initialize Awesome Oscillator strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or AwesomeOscillatorConfig()
    
    @property
    def name(self) -> str:
        return "awesome_oscillator"
    
    def calculate_sma(self, closes: List[float], period: int) -> float:
        """Calculate SMA
        
        Args:
            closes: Close prices
            period: SMA period
            
        Returns:
            SMA value
        """
        if len(closes) < period:
            return sum(closes) / len(closes) if closes else 0.0
        
        return sum(closes[-period:]) / period
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Awesome Oscillator signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with AO analysis
        """
        # Validate klines
        min_required = self.config.slow_period
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
        
        # Calculate SMAs
        ma_fast = self.calculate_sma(closes, self.config.fast_period)
        ma_slow = self.calculate_sma(closes, self.config.slow_period)
        
        # Generate signal
        if ma_fast > ma_slow:
            signal = Signal.BUY
            trend = "uptrend"
        elif ma_fast < ma_slow:
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
                "ma_fast": ma_fast,
                "ma_slow": ma_slow,
                "oscillator": ma_fast - ma_slow,
                "trend": trend,
            },
        )
