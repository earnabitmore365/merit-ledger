#!/usr/bin/env python3
"""
ATR Strategy - Average True Range

Volatility-based trading strategy.

Features:
- ATR calculation for market volatility
- VWAP for trend direction

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class ATRConfig:
    """ATR strategy configuration"""
    atr_period: int = 14
    vwap_period: int = 20


class ATR(Strategy):
    """ATR + VWAP trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[ATRConfig] = None):
        """Initialize ATR strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or ATRConfig()
    
    @property
    def name(self) -> str:
        return "atr"
    
    def calculate_atr(self, klines: List[Dict], period: int = None) -> float:
        """Calculate Average True Range
        
        Args:
            klines: OHLCV data
            period: ATR period
            
        Returns:
            ATR value
        """
        if period is None:
            period = self.config.atr_period
        
        if len(klines) < period + 1:
            return 0.0
        
        tr_list = []
        
        for i in range(1, len(klines)):
            high = klines[i]["high"]
            low = klines[i]["low"]
            prev_close = klines[i - 1]["close"]
            
            # True Range
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            tr_list.append(tr)
        
        if not tr_list:
            return 0.0
        
        if len(tr_list) < period:
            return sum(tr_list) / len(tr_list)
        
        # ATR = Simple Moving Average
        return sum(tr_list[-period:]) / period
    
    def calculate_vwap(
        self, klines: List[Dict], period: int = None
    ) -> float:
        """Calculate Volume Weighted Average Price
        
        Args:
            klines: OHLCV data
            period: VWAP period
            
        Returns:
            VWAP value
        """
        if period is None:
            period = self.config.vwap_period
        
        if len(klines) < period:
            return sum(c["close"] for c in klines) / len(klines)
        
        tp_sum = 0.0
        vol_sum = 0.0
        
        for c in klines[-period:]:
            tp = (c["high"] + c["low"] + c["close"]) / 3
            tp_sum += tp * c.get("volume", 1000)
            vol_sum += c.get("volume", 1000)
        
        return tp_sum / vol_sum if vol_sum else 0.0
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate ATR trading signal
        
        ATR Strategy:
        - Uses ATR to measure volatility
        - Price must be 1 ATR away from VWAP to confirm trend
        - This filters out noise and weak signals
        
        Logic:
        - Price > VWAP + ATR = BUY (confirmed uptrend)
        - Price < VWAP - ATR = SELL (confirmed downtrend)
        - VWAP - ATR < Price < VWAP + ATR = HOLD (consolidation/noise)
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with ATR analysis
        """
        # Validate klines
        min_required = max(self.config.atr_period, self.config.vwap_period) + 5
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # Calculate indicators
        atr = self.calculate_atr(klines)
        vwap = self.calculate_vwap(klines)
        
        if vwap == 0:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={"reason": "VWAP calculation failed"},
            )
        
        current = klines[-1]["close"]
        
        # Distance from VWAP in ATR units
        atr_distance = current - vwap
        
        # Generate signal based on ATR confirmation
        if atr_distance > atr:
            # Price is above VWAP by more than ATR = confirmed uptrend
            signal = Signal.BUY
            confidence = min(abs(atr_distance) / atr * 0.5, 1.0)
            trend = "uptrend"
        
        elif atr_distance < -atr:
            # Price is below VWAP by more than ATR = confirmed downtrend
            signal = Signal.SELL
            confidence = min(abs(atr_distance) / atr * 0.5, 1.0)
            trend = "downtrend"
        
        else:
            # Price is within 1 ATR of VWAP = consolidation/noise
            signal = Signal.HOLD
            confidence = 0.0
            trend = "consolidation"
        
        return TradingSignal(
            signal=signal,
            confidence=confidence,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "atr": atr,
                "vwap": vwap,
                "price": current,
                "trend": trend,
                "volatility": atr,
                "atr_distance": atr_distance,
            },
        )
