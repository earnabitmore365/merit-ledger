#!/usr/bin/env python3
"""
CMF Strategy - Chaikin Money Flow

Volume-based money flow indicator.

Features:
- Money Flow calculation
- Positive/negative flow signals

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class CMFConfig:
    """CMF strategy configuration"""
    period: int = 20


class CMF(Strategy):
    """Chaikin Money Flow trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[CMFConfig] = None):
        """Initialize CMF strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or CMFConfig()
    
    @property
    def name(self) -> str:
        return "cmf"
    
    def calculate_money_flow(
        self, closes: List[float], highs: List[float], lows: List[float], volumes: List[float]
    ) -> float:
        """Calculate Money Flow
        
        Args:
            closes: Close prices
            highs: High prices
            lows: Low prices
            volumes: Volume data
            
        Returns:
            Money flow value
        """
        if len(closes) != len(highs) or len(closes) != len(lows):
            return 0.0
        
        mf_sum = 0.0
        vol_sum = 0.0
        
        for c, h, l, v in zip(closes, highs, lows, volumes):
            typical_price = (h + l + c) / 3
            mf = typical_price * v
            mf_sum += mf
            vol_sum += v
        
        return mf_sum / vol_sum if vol_sum > 0 else 0.0
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate CMF trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with money flow analysis
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
        
        # Extract data
        closes = [c["close"] for c in klines[-self.config.period :]]
        highs = [c["high"] for c in klines[-self.config.period :]]
        lows = [c["low"] for c in klines[-self.config.period :]]
        volumes = [c.get("volume", 1000) for c in klines[-self.config.period :]]
        
        # Calculate Money Flow
        mf = self.calculate_money_flow(closes, highs, lows, volumes)
        
        # Generate signal
        if mf > 0:
            signal = Signal.BUY
            trend = "money_inflow"
        elif mf < 0:
            signal = Signal.SELL
            trend = "money_outflow"
        else:
            signal = Signal.HOLD
            trend = "neutral"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "money_flow": mf,
                "trend": trend,
            },
        )
