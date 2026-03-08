#!/usr/bin/env python3
"""
BB Squeeze Strategy - Simple Bollinger Bands Strategy

Simple Bollinger Bands breakout strategy.
参考旧系统 (auto-trading) 的实现。

布林带:
- 中轨: 20日 SMA
- 上轨: 中轨 + 2倍标准差  
- 下轨: 中轨 - 2倍标准差

策略:
- 价格触及下轨 -> 买入
- 价格触及上轨 -> 卖出
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

from src.core.strategy import Strategy, Signal, TradingSignal


@dataclass
class BBSqueezeConfig:
    """BB Squeeze strategy configuration"""
    bb_period: int = 20
    bb_std: float = 2.0


class BBSqueeze(Strategy):
    """Bollinger Bands Squeeze trading strategy"""
    
    def __init__(self, exchange=None, config: Optional[BBSqueezeConfig] = None):
        """Initialize BB Squeeze strategy
        
        Args:
            exchange: Exchange adapter
            config: Strategy configuration
        """
        self.exchange = exchange
        self.config = config or BBSqueezeConfig()
    
    @property
    def name(self) -> str:
        return "bb_squeeze"
    
    def calculate_bollinger_bands(self, prices: List[float]) -> Dict:
        """Calculate current Bollinger Bands (fast - returns only current values)
        
        Args:
            prices: Price series
            
        Returns:
            Dict with current upper, middle, lower values
        """
        period = self.config.bb_period
        if len(prices) < period:
            return {
                'upper': prices[-1],
                'middle': prices[-1],
                'lower': prices[-1]
            }
        
        recent = prices[-period:]
        middle = sum(recent) / period
        
        # 计算标准差
        variance = sum((p - middle) ** 2 for p in recent) / period
        std = math.sqrt(variance)
        
        return {
            'upper': middle + (std * self.config.bb_std),
            'middle': middle,
            'lower': middle - (std * self.config.bb_std)
        }
    
    def calculate_bollinger_bands_array(self, prices: List[float]) -> Tuple[List[float], List[float], List[float]]:
        """Calculate ALL Bollinger Bands values (for backtest pre-computation)
        
        Args:
            prices: Price series
            
        Returns:
            Tuple of (middle, upper, lower) arrays
        """
        period = self.config.bb_period
        n = len(prices)
        
        middle = []
        upper = []
        lower = []
        
        for i in range(n):
            if i < period:
                middle.append(prices[i])
                upper.append(prices[i])
                lower.append(prices[i])
            else:
                recent = prices[i - period + 1:i + 1]
                sma = sum(recent) / period
                
                variance = sum((p - sma) ** 2 for p in recent) / period
                std = math.sqrt(variance)
                
                middle.append(sma)
                upper.append(sma + std * self.config.bb_std)
                lower.append(sma - std * self.config.bb_std)
        
        return middle, upper, lower
    
    def generate_signal(
        self, coin: str, klines: List[Dict] = None
    ) -> TradingSignal:
        """Generate BB Squeeze trading signal
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            
        Returns:
            TradingSignal with signal
        """
        # Validate klines
        min_required = self.config.bb_period
        if not klines or len(klines) < min_required:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # Extract close prices
        closes = [c["close"] for c in klines]
        current = closes[-1]
        
        # Calculate Bollinger Bands
        bb = self.calculate_bollinger_bands(closes)
        
        # Generate signal
        if current < bb['lower']:
            # 价格触及下轨 -> 买入
            return TradingSignal(
                signal=Signal.BUY,
                confidence=0.7,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={
                    "reason": "Price touched lower band",
                    "upper": bb['upper'],
                    "middle": bb['middle'],
                    "lower": bb['lower'],
                    "current": current
                }
            )
        if current > bb['upper']:
            # 价格触及上轨 -> 卖出
            return TradingSignal(
                signal=Signal.SELL,
                confidence=0.7,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={
                    "reason": "Price touched upper band",
                    "upper": bb['upper'],
                    "middle": bb['middle'],
                    "lower": bb['lower'],
                    "current": current
                }
            )
        else:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={
                    "reason": "Price within bands",
                    "upper": bb['upper'],
                    "middle": bb['middle'],
                    "lower": bb['lower'],
                    "current": current
                }
            )
    
    def generate_signal_fast(
        self,
        coin: str,
        klines: List[Dict],
        indicator_arrays: Dict,
        current_idx: int
    ) -> TradingSignal:
        """Generate signal using pre-computed Bollinger Bands (for backtesting)
        
        Args:
            coin: Trading pair
            klines: OHLCV data
            indicator_arrays: Pre-computed arrays
            current_idx: Current candle index
            
        Returns:
            TradingSignal
        """
        if not klines or len(klines) < self.config.bb_period:
            return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"] if klines else 0,
                metadata={"reason": "Insufficient klines"},
            )
        
        # 使用预计算的布林带值
        closes = indicator_arrays['closes']
        upper = indicator_arrays['upper']
        lower = indicator_arrays['lower']
        
        current = closes[current_idx]
        current_upper = upper[current_idx]
        current_lower = lower[current_idx]
        
        if current < current_lower:
            return TradingSignal(
                signal=Signal.BUY,
                confidence=0.7,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={
                    "reason": "Price touched lower band",
                    "upper": current_upper,
                    "lower": current_lower,
                    "current": current
                }
            )
        if current > current_upper:
            return TradingSignal(
                signal=Signal.SELL,
                confidence=0.7,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={
                    "reason": "Price touched upper band",
                    "upper": current_upper,
                    "lower": current_lower,
                    "current": current
                }
            )
        return TradingSignal(
                signal=Signal.HOLD,
                confidence=0.0,
                coin=coin,
                timestamp=klines[-1]["time"],
                metadata={
                    "reason": "Price within bands",
                    "upper": current_upper,
                    "lower": current_lower,
                    "current": current
                }
            )
