#!/usr/bin/env python3
"""
Klinger Strategy

Klinger Volume Oscillator.

Features:
- Volume EMA difference
- Signal line crossover
- Price trend confirmation

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class KlingerConfig:
    """Klinger configuration"""
    ema_fast: int = 34
    ema_slow: int = 55
    signal_period: int = 13


class Klinger(Strategy):
    """Klinger Volume Oscillator trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[KlingerConfig] = None):
        """Initialize Klinger strategy"""
        self.exchange = exchange
        self.config = config or KlingerConfig()
    
    @property
    def name(self) -> str:
        return "klinger_echo"
    
    def calculate_ema(self, data: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(data) < period:
            return sum(data) / len(data) if data else 0.0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for value in data[period:]:
            ema = (value - ema) * multiplier + ema
        return ema
    
    def calculate_klinger(self, klines: List[Dict]) -> Dict:
        """Calculate KVO"""
        if len(klines) < self.config.ema_slow:
            return {"kvo": 0.0, "signal": 0.0, "trend": 0.0}
        
        volumes = [c.get("volume", 1) for c in klines]
        ema_34 = self.calculate_ema(volumes, self.config.ema_fast)
        ema_55 = self.calculate_ema(volumes, self.config.ema_slow)
        kvo = ema_34 - ema_55
        
        closes = [c["close"] for c in klines]
        trend = closes[-1] - closes[-10]
        
        return {"kvo": kvo, "signal": 0.0, "trend": trend}
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Klinger signal"""
        min_required = self.config.ema_slow + 10
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        kvo_data = self.calculate_klinger(klines)
        kvo_prev = self.calculate_klinger(klines[:-1])
        
        kvo = kvo_data["kvo"]
        kvo_prev_val = kvo_prev["kvo"]
        trend = kvo_data["trend"]
        
        if kvo_prev_val <= 0 and kvo > 0:
            signal = Signal.BUY
        if kvo_prev_val >= 0 and kvo < 0:
            signal = Signal.SELL
        if kvo > 0 and trend > 0:
            signal = Signal.BUY
        elif kvo < 0 and trend < 0:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={"kvo": kvo, "trend": trend},
        )
