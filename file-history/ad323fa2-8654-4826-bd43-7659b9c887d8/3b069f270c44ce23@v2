#!/usr/bin/env python3
"""
MA RSI Strategy

MA + RSI 策略
- 简单移动平均线交叉
- RSI 过滤器
"""

from typing import Dict, List
from src.core.strategy.base import Strategy, Signal


class MARSIStrategy(Strategy):
    """MA + RSI 交易策略"""

    def __init__(self):
        super().__init__("ma_rsi")
        self.ma_period = 20
        self.rsi_period = 14

    def calculate_ma(self, closes: List[float]) -> float:
        """计算简单移动平均"""
        if len(closes) < self.ma_period:
            return sum(closes) / len(closes)
        return sum(closes[-self.ma_period:]) / self.ma_period

    def calculate_rsi(self, closes: List[float]) -> float:
        """计算 RSI"""
        if len(closes) < self.rsi_period + 1:
            return 50.0

        gains = 0.0
        losses = 0.0

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            if change > 0:
                gains += change
            else:
                losses += abs(change)

        if losses == 0:
            return 100.0

        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signal(self, coin: str, klines: List[Dict]) -> Signal:
        """生成 MA RSI 交易信号

        Args:
            coin: 交易对
            klines: K 线数据

        Returns:
            Signal: BUY, SELL, 或 HOLD
        """
        if not klines or len(klines) < 30:
            return Signal.HOLD

        closes = [k["close"] for k in klines]

        ma = self.calculate_ma(closes)
        rsi = self.calculate_rsi(closes)

        if closes[-1] > ma and rsi < 50:
            return Signal.BUY
        if closes[-1] < ma and rsi > 50:
            return Signal.SELL
        return Signal.HOLD
