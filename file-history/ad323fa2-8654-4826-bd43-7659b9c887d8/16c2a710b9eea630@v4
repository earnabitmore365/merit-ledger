#!/usr/bin/env python3
"""
VWAP Strategy

VWAP 策略
- 价格高于 VWAP = 买入
- 价格低于 VWAP = 卖出
- 其他 = 持有
"""

from typing import Dict, List
from core.strategy.base import Strategy, Signal


class VWAPStrategy(Strategy):
    """VWAP 交易策略"""

    def __init__(self):
        super().__init__("vwap")
        self.period = 20

    def calculate_vwap(self, klines: List[Dict]) -> float:
        """计算 VWAP"""
        if len(klines) < self.period:
            return sum(k["close"] for k in klines) / len(klines)

        tp_sum = 0.0
        vol_sum = 0.0

        for k in klines[-self.period:]:
            typical_price = (k["high"] + k["low"] + k["close"]) / 3
            volume = k.get("volume", 1000)
            tp_sum += typical_price * volume
            vol_sum += volume

        return tp_sum / vol_sum if vol_sum else 0

    def generate_signal(self, coin: str, klines: List[Dict]) -> Signal:
        """生成 VWAP 交易信号

        Args:
            coin: 交易对
            klines: K 线数据

        Returns:
            Signal: BUY, SELL, 或 HOLD
        """
        if not klines or len(klines) < self.period:
            return Signal.HOLD

        vwap = self.calculate_vwap(klines)
        current_price = klines[-1]["close"]

        if current_price > vwap:
            return Signal.BUY
        elif current_price < vwap:
            return Signal.SELL
        return Signal.HOLD
