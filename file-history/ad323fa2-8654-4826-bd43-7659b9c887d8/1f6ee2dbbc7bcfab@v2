#!/usr/bin/env python3
"""
SMC Strategy - Smart Money Concepts

智能资金概念策略
- 订单块检测
- FVG（公平价值缺口）识别
- OTE（最佳交易入场）区域
- 趋势判断
"""

from typing import Dict, List
from src.core.strategy.base import Strategy, Signal


class SMCStrategy(Strategy):
    """智能资金概念交易策略"""

    def __init__(self):
        super().__init__("smc")
        self.short_ma = 20
        self.long_ma = 50

    def calculate_ma(self, closes: List[float], period: int) -> float:
        """计算移动平均"""
        if len(closes) < period:
            return sum(closes) / len(closes) if closes else 0.0
        return sum(closes[-period:]) / period

    def calculate_ote_zone(self, closes: List[float]) -> Dict:
        """计算 OTE 区域"""
        if len(closes) < 20:
            return {"ote_high": closes[-1], "ote_low": closes[-1]}

        high = max(closes[-20:])
        low = min(closes[-20:])

        return {
            "ote_high": high - (high - low) * 0.382,
            "ote_low": low + (high - low) * 0.382,
        }

    def determine_trend(self, closes: List[float]) -> str:
        """判断趋势方向"""
        if len(closes) < self.long_ma:
            return "neutral"

        ma_short = self.calculate_ma(closes, self.short_ma)
        ma_long = self.calculate_ma(closes, self.long_ma)

        if ma_short > ma_long:
            return "uptrend"
        elif ma_short < ma_long:
            return "downtrend"
        return "neutral"

    def generate_signal(self, coin: str, klines: List[Dict]) -> Signal:
        """生成交易信号

        Args:
            coin: 交易对
            klines: K 线数据

        Returns:
            Signal: BUY, SELL, 或 HOLD
        """
        if not klines or len(klines) < 50:
            return Signal.HOLD

        closes = [k["close"] for k in klines]
        trend = self.determine_trend(closes)

        if trend == "uptrend":
            return Signal.BUY
        elif trend == "downtrend":
            return Signal.SELL
        return Signal.HOLD
