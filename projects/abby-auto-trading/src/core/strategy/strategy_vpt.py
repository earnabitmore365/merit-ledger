#!/usr/bin/env python3
"""
VPT Strategy - Volume Price Trend

Volume-based momentum indicator.

Features:
- Price change percentage
- Volume-weighted accumulation

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class VPTConfig:
    """VPT configuration"""
    period: int = 20


class VPT(Strategy):
    """Volume Price Trend trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[VPTConfig] = None):
        """Initialize VPT strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or VPTConfig()
    
    @property
    def name(self) -> str:
        return "vpt"
    
    def calculate_vpt(self, klines: List[Dict]) -> float:
        """Calculate VPT
        
        Args:
            klines: OHLCV data
            
        Returns:
            VPT value
        """
        if len(klines) < 2:
            return 0.0
        
        vpt = 0.0
        closes = [c["close"] for c in klines]
        volumes = [c.get("volume", 1000) for c in klines]
        
        for i in range(1, len(klines)):
            if closes[i - 1] == 0:
                continue
            price_change = (closes[i] - closes[i - 1]) / closes[i - 1]
            vpt += price_change * volumes[i]
        
        return vpt
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate VPT signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with VPT analysis
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
        
        # Calculate VPT
        vpt = self.calculate_vpt(klines)
        
        # Generate signal
        if vpt > 0:
            signal = Signal.BUY
            trend = "accumulation"
        elif vpt < 0:
            signal = Signal.SELL
            trend = "distribution"
        else:
            signal = Signal.HOLD
            trend = "neutral"
        
        return TradingSignal(
            signal=signal,
            confidence=min(abs(vpt) / 1000, 1.0),
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "vpt": vpt,
                "trend": trend,
            },
        )
