#!/usr/bin/env python3
"""
Candlestick Strategy

Candlestick pattern recognition strategy.

Features:
- Pattern identification
- Trend confirmation

Migrated from echo-auto-trading project.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class CandlestickConfig:
    """Candlestick configuration"""
    period: int = 20


class Candlestick(Strategy):
    """Candlestick pattern trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[CandlestickConfig] = None):
        """Initialize Candlestick strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or CandlestickConfig()
    
    @property
    def name(self) -> str:
        return "klinestick"
    
    def _analyze_candle(self, candle: Dict) -> Dict:
        """Analyze single candle
        
        Args:
            candle: OHLCV data
            
        Returns:
            Analysis dictionary
        """
        body = abs(candle["close"] - candle["open"])
        upper_wick = candle["high"] - max(candle["open"], candle["close"])
        lower_wick = min(candle["open"], candle["close"]) - candle["low"]
        total_range = candle["high"] - candle["low"]
        
        if total_range == 0:
            total_range = 1
        
        return {
            "body": body,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
            "body_ratio": body / total_range,
            "is_bullish": candle["close"] > candle["open"],
        }
    
    def identify_pattern(self, klines: List[Dict]) -> str:
        """Identify klinestick pattern
        
        Args:
            klines: OHLCV data
            
        Returns:
            Pattern name
        """
        if len(klines) < 3:
            return "NORMAL"
        
        latest = self._analyze_candle(klines[-1])
        body = latest["body"]
        upper_wick = latest["upper_wick"]
        lower_wick = latest["lower_wick"]
        is_bullish = latest["is_bullish"]
        
        # Hammer
        if lower_wick > body * 2 and upper_wick < body * 0.5:
            return "hammer" if is_bullish else "hanging_man"
        
        # Shooting star
        if upper_wick > body * 2 and lower_wick < body * 0.5:
            return "shooting_star" if not is_bullish else "inverted_hammer"
        
        # Doji
        if latest["body_ratio"] < 0.1:
            return "doji"
        
        # Strong candle
        if latest["body_ratio"] > 0.7:
            return "strong_bullish" if is_bullish else "strong_bearish"
        
        return "NORMAL"
    
    def get_trend(self, klines: List[Dict]) -> str:
        """Determine trend direction
        
        Args:
            klines: OHLCV data
            
        Returns:
            Trend direction
        """
        if len(klines) < self.config.period:
            return "unknown"
        
        closes = [c["close"] for c in klines]
        ma_short = sum(closes[-5:]) / 5
        ma_long = sum(closes[-self.config.period :]) / self.config.period
        
        if ma_short > ma_long:
            return "uptrend"
        elif ma_short < ma_long:
            return "downtrend"
        else:
            return "ranging"
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate Candlestick signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with pattern analysis
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
        
        # Analyze pattern
        pattern = self.identify_pattern(klines)
        trend = self.get_trend(klines)
        
        # Generate signal
        bullish_patterns = ["hammer", "strong_bullish"]
        bearish_patterns = ["hanging_man", "strong_bearish"]
        
        if pattern in bullish_patterns:
            signal = Signal.BUY
            confidence = 0.6
        elif pattern in bearish_patterns:
            signal = Signal.SELL
            confidence = 0.6
        else:
            signal = Signal.HOLD
            confidence = 0.3
        
        return TradingSignal(
            signal=signal,
            confidence=confidence,
            coin=coin,
            timestamp=klines[-1]["time"],
            metadata={
                "pattern": pattern,
                "trend": trend,
            },
        )
