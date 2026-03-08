#!/usr/bin/env python3
"""
Heikin Ashi Strategy

Average price klinestick strategy.

Features:
- Heikin Ashi candle calculation
- Trend detection from consecutive klines
- Auto-migrated from echo-auto-trading project
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class HeikinAshiConfig:
    """Heikin Ashi strategy configuration"""
    min_klines: int = 5


class HeikinAshiStrategy(Strategy):
    """Heikin Ashi klinestick strategy"""
    
    def __init__(self, exchange=None, config: Optional[HeikinAshiConfig] = None):
        """Initialize Heikin Ashi strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or HeikinAshiConfig()
    
    @property
    def name(self) -> str:
        return "heikin_ashi"
    
    def calculate_heikin_ashi(self, klines: List[Dict]) -> List[Dict]:
        """Calculate Heikin Ashi klines
        
        Args:
            klines: Original OHLCV klines
            
        Returns:
            List of Heikin Ashi klines
        """
        if not klines or len(klines) < 2:
            return []
        
        ha_klines = []
        prev_ha_open = None
        prev_ha_close = None
        
        for i, candle in enumerate(klines):
            ha_close = (candle["open"] + candle["high"] + candle["low"] + candle["close"]) / 4
            
            if i == 0:
                ha_open = (candle["open"] + candle["close"]) / 2
            else:
                ha_open = (prev_ha_open + prev_ha_close) / 2
            
            ha_high = max(candle["high"], ha_open, ha_close)
            ha_low = min(candle["low"], ha_open, ha_close)
            
            ha_candle = {
                "time": candle["time"],
                "open": ha_open,
                "high": ha_high,
                "low": ha_low,
                "close": ha_close,
                "volume": candle["volume"],
            }
            
            ha_klines.append(ha_candle)
            prev_ha_open = ha_open
            prev_ha_close = ha_close
        
        return ha_klines
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Heikin Ashi trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with direction and confidence
        """
        # Validate klines
        if not klines or len(klines) < self.config.min_klines:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # Calculate Heikin Ashi
        ha_klines = self.calculate_heikin_ashi(klines)
        
        if not ha_klines or len(ha_klines) < 2:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Heikin Ashi calculation failed"},
            )
        
        # Get recent klines
        prev_ha = ha_klines[-2]
        curr_ha = ha_klines[-1]
        
        # Determine trend
        prev_bullish = prev_ha["open"] < prev_ha["close"]
        curr_bullish = curr_ha["open"] < curr_ha["close"]
        prev_bearish = prev_ha["open"] > prev_ha["close"]
        curr_bearish = curr_ha["open"] > curr_ha["close"]
        
        # Generate signal
        if prev_bullish and curr_bullish:
            # Consecutive bullish klines - uptrend
            signal = Signal.BUY
            confidence = 0.7
            trend = "uptrend"
        elif prev_bearish and curr_bearish:
            # Consecutive bearish klines - downtrend
            signal = Signal.SELL
            confidence = 0.7
            trend = "downtrend"
        else:
            # No clear trend
            signal = Signal.HOLD
            confidence = 0.3
            trend = "consolidation"
        
        return TradingSignal(
            signal=signal,
            confidence=confidence,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "prev_bullish": prev_bullish,
                "curr_bullish": curr_bullish,
                "trend": trend,
            },
        )
