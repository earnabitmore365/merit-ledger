#!/usr/bin/env python3
"""
Demand Index Strategy

Demand Index indicator.

Features:
- Price-volume relationship
- Supply/demand pressure

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class DemandIndexConfig:
    """Demand Index configuration"""
    period: int = 20


class DemandIndex(Strategy):
    """Demand Index trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[DemandIndexConfig] = None):
        """Initialize Demand Index strategy"""
        self.exchange = exchange
        self.config = config or DemandIndexConfig()
    
    @property
    def name(self) -> str:
        return "demand_index_echo"
    
    def calculate_di(self, klines: List[Dict]) -> float:
        """Calculate Demand Index"""
        if len(klines) < self.config.period:
            return 0.0
        price_changes = []
        volumes = []
        for i in range(1, len(klines)):
            change = klines[i]["close"] - klines[i - 1]["close"]
            price_changes.append(change)
            volumes.append(klines[i].get("volume", 1))
        weighted = sum(pc * v for pc, v in zip(price_changes[-20:], volumes[-20:]))
        vol_sum = sum(volumes[-20:])
        if vol_sum == 0:
            return 0.0
        return (weighted / vol_sum) * 100
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Demand Index signal"""
        min_required = self.config.period
        if not klines or len(klines) < min_required:
            return TradingSignal(signal=Signal.HOLD, confidence=0.0, coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"})
        di = self.calculate_di(klines)
        di_prev = self.calculate_di(klines[:-1])
        if di > 0 and di_prev <= 0:
            signal = Signal.BUY
        if di < 0 and di_prev >= 0:
            signal = Signal.SELL
        if di_prev < 0 and di >= 0:
            signal = Signal.BUY
        if di_prev >= 0 and di < 0:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
        return TradingSignal(signal=signal, confidence=0.6, coin=coin,
            timestamp=klines[-1]["time"], metadata={"di": di})
