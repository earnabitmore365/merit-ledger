#!/usr/bin/env python3
"""
CMO Strategy - Chande Momentum Oscillator

Momentum oscillator.

Features:
- Momentum strength calculation
- Zero line crossovers

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class CMOConfig:
    """CMO strategy configuration"""
    short_period: int = 9
    long_period: int = 20


class CMO(Strategy):
    """Chande Momentum Oscillator trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[CMOConfig] = None):
        """Initialize CMO strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or CMOConfig()
    
    @property
    def name(self) -> str:
        return "cmo"
    
    def calculate_cmo(self, prices: List[float], period: int) -> float:
        """Calculate Chande Momentum Oscillator
        
        Args:
            prices: Price series
            period: CMO period
            
        Returns:
            CMO value (-100 to 100)
        """
        if len(prices) < period + 1:
            return 0.0
        
        ups = 0.0
        downs = 0.0
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                ups += change
            elif change < 0:
                downs += abs(change)
        
        total = ups + downs
        if total == 0:
            return 0.0
        
        return (ups - downs) / total * 100
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate CMO trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with momentum analysis
        """
        # Validate klines
        min_required = 30
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # Extract prices
        prices = [c["close"] for c in klines]
        
        # Calculate CMO
        cmo = self.calculate_cmo(prices, self.config.short_period)
        prev_cmo = self.calculate_cmo(prices[:-1], self.config.short_period)
        
        # Generate signal
        if prev_cmo <= 0 and cmo > 0:
            signal = Signal.BUY
            trend = "momentum_up"
        if prev_cmo >= 0 and cmo < 0:
            signal = Signal.SELL
            trend = "momentum_down"
        if cmo > prev_cmo and cmo > 10:
            signal = Signal.BUY
            trend = "strengthening"
        elif cmo < prev_cmo and cmo < -10:
            signal = Signal.SELL
            trend = "weakening"
        else:
            signal = Signal.HOLD
            trend = "neutral"
        
        return TradingSignal(
            signal=signal,
            confidence=abs(cmo) / 100,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "cmo": cmo,
                "prev_cmo": prev_cmo,
                "trend": trend,
            },
        )
