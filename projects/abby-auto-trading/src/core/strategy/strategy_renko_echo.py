#!/usr/bin/env python3
"""
Renko Strategy

Renko brick analysis.

Features:
- ATR-based brick size
- Brick direction tracking
- Trend reversal signals

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class RenkoConfig:
    """Renko configuration"""
    atr_period: int = 14
    brick_pct: float = 0.02


class Renko(Strategy):
    """Renko trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[RenkoConfig] = None):
        """Initialize Renko strategy"""
        self.exchange = exchange
        self.config = config or RenkoConfig()
    
    @property
    def name(self) -> str:
        return "renko_echo"
    
    def calculate_atr(self, klines: List[Dict]) -> float:
        """Calculate ATR"""
        if len(klines) < self.config.atr_period + 1:
            return klines[-1]["close"] * self.config.brick_pct
        
        tr_list = []
        for i in range(1, len(klines)):
            high = klines[i]["high"]
            low = klines[i]["low"]
            prev_close = klines[i - 1]["close"]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
        
        return sum(tr_list[-self.config.atr_period :]) / self.config.atr_period
    
    def generate_bricks(self, closes: List[float], brick_size: float) -> List[str]:
        """Generate Renko bricks"""
        if len(closes) < 2:
            return []
        
        bricks = []
        direction = None
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            
            if direction is None:
                if abs(change) >= brick_size:
                    direction = 1 if change > 0 else -1
                    bricks.append("UP" if direction == 1 else "DOWN")
            
            elif direction == 1:
                if change >= brick_size:
                    bricks.append("UP")
                elif change <= -brick_size:
                    direction = -1
                    bricks.append("DOWN")
            
            elif direction == -1:
                if change <= -brick_size:
                    bricks.append("DOWN")
                if change >= brick_size:
                    direction = 1
                    bricks.append("UP")
        
        return bricks
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Renko signal"""
        min_required = 50
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        closes = [c["close"] for c in klines]
        atr = self.calculate_atr(klines)
        brick_size = max(atr, closes[-1] * self.config.brick_pct)
        bricks = self.generate_bricks(closes, brick_size)
        
        if len(bricks) < 2:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={"reason": "Not enough bricks"},
            )
        
        if bricks[-1] == "UP" and bricks[-2] == "UP":
            signal = Signal.BUY
            trend = "uptrend"
        elif bricks[-1] == "DOWN" and bricks[-2] == "DOWN":
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
            metadata={"bricks": bricks[-5:], "trend": trend},
        )
