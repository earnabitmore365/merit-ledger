#!/usr/bin/env python3
"""
TVI Strategy - Trade Volume Index

Volume-based accumulation indicator.

Features:
- Price change accumulation
- Volume-weighted trend

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class TVIConfig:
    """TVI configuration"""
    period: int = 20


class TVI(Strategy):
    """Trade Volume Index trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[TVIConfig] = None):
        """Initialize TVI strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or TVIConfig()
    
    @property
    def name(self) -> str:
        return "tvi"
    
    def calculate_tvi(self, klines: List[Dict]) -> float:
        """Calculate TVI
        
        Args:
            klines: OHLCV data
            
        Returns:
            TVI value
        """
        if len(klines) < self.config.period:
            return 0.0
        
        closes = [c["close"] for c in klines[-self.config.period :]]
        
        if closes[0] == 0:
            return 0.0
        
        change = (closes[-1] - closes[0]) / closes[0] * 100
        
        return change
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate TVI signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with TVI analysis
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
        
        # Calculate TVI
        tvi = self.calculate_tvi(klines)
        
        # Generate signal
        if tvi > 0:
            signal = Signal.BUY
            trend = "accumulation"
        elif tvi < 0:
            signal = Signal.SELL
            trend = "distribution"
        else:
            signal = Signal.HOLD
            trend = "neutral"
        
        return TradingSignal(
            signal=signal,
            confidence=min(abs(tvi) / 10, 1.0),
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "tvi": tvi,
                "trend": trend,
            },
        )
