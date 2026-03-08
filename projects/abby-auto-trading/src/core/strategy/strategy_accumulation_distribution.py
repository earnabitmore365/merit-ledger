#!/usr/bin/env python3
"""
Accumulation Distribution Strategy

A/D Line indicator.

Features:
- Money flow calculation
- Accumulation/Distribution signals

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class AccumulationDistributionConfig:
    """A/D configuration"""
    period: int = 20


class AccumulationDistribution(Strategy):
    """Accumulation/Distribution trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[AccumulationDistributionConfig] = None):
        """Initialize A/D strategy"""
        self.exchange = exchange
        self.config = config or AccumulationDistributionConfig()
    
    @property
    def name(self) -> str:
        return "accumulation_distribution"
    
    def calculate_ad(self, klines: List[Dict]) -> float:
        """Calculate A/D Line"""
        if len(klines) < 2:
            return 0.0
        
        ad_sum = 0.0
        for i in range(1, len(klines)):
            closes = klines[i]["close"]
            highs = klines[i]["high"]
            lows = klines[i]["low"]
            volumes = klines[i].get("volume", 1000)
            
            typical_price = (highs + lows + closes) / 3
            ad_sum += typical_price * volumes
        
        return ad_sum
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate A/D signal"""
        min_required = self.config.period
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        ad = self.calculate_ad(klines[-self.config.period :])
        
        if ad > 0:
            signal = Signal.BUY
            trend = "accumulation"
        elif ad < 0:
            signal = Signal.SELL
            trend = "distribution"
        else:
            signal = Signal.HOLD
            trend = "neutral"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={"ad": ad, "trend": trend},
        )
