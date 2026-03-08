#!/usr/bin/env python3
"""
ATR Trailing Stop Strategy

ATR-based trailing stop strategy.

Features:
- ATR calculation
- Dynamic stop levels

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from core.strategy import Strategy, Signal, TradingSignal


@dataclass
class ATRTrailingStopConfig:
    """ATR Trailing Stop configuration"""
    atr_period: int = 14
    multiplier: float = 2.0
    lookback: int = 20


class ATRTrailingStop(Strategy):
    """ATR Trailing Stop trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[ATRTrailingStopConfig] = None):
        """Initialize ATR Trailing Stop strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or ATRTrailingStopConfig()
    
    @property
    def name(self) -> str:
        return "atr_trailing_stop"
    
    def calculate_atr(self, klines: List[Dict]) -> float:
        """Calculate ATR
        
        Args:
            klines: OHLCV data
            
        Returns:
            ATR value
        """
        if len(klines) < 2:
            return 0.0
        
        tr_list = []
        for i in range(1, len(klines)):
            high = klines[i]["high"]
            low = klines[i]["low"]
            prev_close = klines[i - 1]["close"]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            tr_list.append(tr)
        
        if len(tr_list) < self.config.atr_period:
            return sum(tr_list) / len(tr_list) if tr_list else 0.0
        
        return sum(tr_list[-self.config.atr_period :]) / self.config.atr_period
    
    def calculate_trailing_stops(
        self, klines: List[Dict], atr: float
    ) -> Dict[str, float]:
        """Calculate trailing stop levels
        
        Args:
            klines: OHLCV data
            atr: ATR value
            
        Returns:
            Dictionary with long_stop and short_stop
        """
        if len(klines) < self.config.lookback:
            return {"long_stop": 0.0, "short_stop": 0.0}
        
        closes = [c["close"] for c in klines[-self.config.lookback :]]
        
        highest_close = max(closes)
        lowest_close = min(closes)
        
        long_stop = highest_close - (atr * self.config.multiplier)
        short_stop = lowest_close + (atr * self.config.multiplier)
        
        return {"long_stop": long_stop, "short_stop": short_stop}
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate ATR Trailing Stop signal

        Args:
            coin: Trading pair
            klines: OHLCV data

        Returns:
            TradingSignal with trailing stop analysis
        """
        # Validate klines
        min_required = self.config.lookback
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )

        # Extract closes
        closes = [k["close"] for k in klines]
        current_price = closes[-1]

        # Calculate ATR
        atr = self.calculate_atr(klines)

        # Calculate trailing stops
        trail = self.calculate_trailing_stops(klines, atr)
        
        # Determine trend using MAs
        ma_short = sum(closes[-10:]) / 10
        ma_long = sum(closes[-25:]) / 25
        
        # Generate signal
        if current_price > ma_short > ma_long:
            # Uptrend
            if current_price < trail["long_stop"]:
                signal = Signal.BUY
                trend = "uptrend_trail_hit"
            else:
                signal = Signal.HOLD
                trend = "uptrend"
        elif current_price < ma_short < ma_long:
            # Downtrend
            if current_price > trail["short_stop"]:
                signal = Signal.SELL
                trend = "downtrend_trail_hit"
            else:
                signal = Signal.HOLD
                trend = "downtrend"
        else:
            signal = Signal.HOLD
            trend = "consolidation"
        
        return TradingSignal(
            signal=signal,
            confidence=0.6,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "atr": atr,
                "long_stop": trail["long_stop"],
                "short_stop": trail["short_stop"],
                "current_price": current_price,
                "trend": trend,
            },
        )
