#!/usr/bin/env python3
"""
TTP Manager

移动止盈管理器
根据价格波动自动调整止盈价位
"""

import logging
from dataclasses import dataclass
from typing import Dict

from .base import RiskManager, RiskConfig, RiskCheckResult


# ==================== 配置类定义 ====================

@dataclass
class TTPConfig(RiskConfig):
    """移动止盈配置

    Attributes:
        ttp_enabled: 是否启用
        ttp_buffer_pips: 回调多少 pips 后设置 TTP
        ttp_trigger_pct: 浮盈达到多少百分比后启动 TTP
    """
    ttp_enabled: bool = True
    ttp_buffer_pips: float = 5.0
    ttp_trigger_pct: float = 0.01  # 1% 浮盈后启动


# ==================== 状态类定义 ====================

@dataclass
class TTPState:
    """TTP 状态"""
    active: bool = False  # TTP 是否激活
    swing_high: float = 0.0  # 多头：历史最高点
    swing_low: float = 0.0   # 空头：历史最低点
    previous_high: float = 0.0  # 多头：前一个高点（用于确认）
    previous_low: float = 0.0   # 空头：前一个低点（用于确认）
    confirmed: bool = False     # 是否已确认趋势（创新高后回落，再创新高）
    ttp_level: float = 0.0   # TTP 触发价位
    entry_price: float = 0.0  # 开仓价格
    position_side: str = ""    # 持仓方向

    def reset(self):
        """重置状态"""
        self.active = False
        self.swing_high = 0.0
        self.swing_low = 0.0
        self.previous_high = 0.0
        self.previous_low = 0.0
        self.confirmed = False
        self.ttp_level = 0.0
        self.entry_price = 0.0
        self.position_side = ""


# ==================== 移动止盈管理器 ====================

class TTPManager(RiskManager):
    """移动止盈管理器

    实现移动止盈（Trailing Take Profit）逻辑：
    1. 价格浮盈 >= 1%
    2. 创新高
    3. 确认继续涨（再次创新高）
    4. 回调形成"前低"
    5. 设置 TTP（基于前低 - pips）
    6. 价格跌破 TTP 时平仓
    """

    def __init__(self, config: TTPConfig = None):
        """初始化"""
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.state = TTPState()

    def check(
        self,
        position: Dict,
        current_price: float,
        entry_price: float = None,
        position_side: str = None,
        **kwargs
    ) -> RiskCheckResult:
        """检查是否触发移动止盈"""
        # 检查是否启用
        if not self.config.ttp_enabled:
            return RiskCheckResult()

        # 获取参数
        if position is None and (entry_price is None or position_side is None):
            return RiskCheckResult()

        coin = position.get('coin', '') if position else ''
        pos_side = position_side or position.get('side', '')
        open_price = entry_price or position.get('entry_price', 0)

        if open_price <= 0:
            return RiskCheckResult()

        # 计算浮盈比例
        if pos_side == "LONG":
            profit_pct = (current_price - open_price) / open_price
        elif pos_side == "SHORT":
            profit_pct = (open_price - current_price) / open_price
        else:
            return RiskCheckResult()

        # 检查是否满足启动条件（只在持仓刚开始时检查）
        if profit_pct < self.config.ttp_trigger_pct and not self.state.active:
            self.state.reset()
            return RiskCheckResult()

        # 更新 TTP 状态
        self._update_state(pos_side, open_price, current_price)

        # 检查是否触发 TTP
        result = self._check_ttp_trigger(current_price, pos_side)

        if result.should_close:
            self.logger.info(
                f"TTP触发: {pos_side} {coin} "
                f"价格 ${current_price:.2f} < TTP ${result.ttp_level:.2f}"
            )
            self.state.reset()

        return result

    def reset(self):
        """重置状态"""
        self.state.reset()

    def _update_state(
        self,
        position_side: str,
        entry_price: float,
        current_price: float
    ):
        """更新 TTP 状态

        规则：
        1. 浮盈 >= ttp_trigger_pct 才能开始追踪
        2. 创新高后，等待确认（价格再次上涨超过之前的最高点）
        3. 确认后，回调的地点才是有效的"前低"
        4. TTP 基于确认后的回调低点来设置
        """
        # 如果是新的持仓，重置状态
        if self.state.position_side != position_side or self.state.entry_price != entry_price:
            self.state.reset()
            self.state.position_side = position_side
            self.state.entry_price = entry_price

        # 计算 pips
        pips = entry_price * self.config.ttp_buffer_pips * 0.0001

        if position_side == "LONG":
            # 多头：需要先有浮盈才能追踪
            profit_pct = (current_price - entry_price) / entry_price
            if profit_pct < self.config.ttp_trigger_pct:
                return  # 浮盈不足

            # 1. 创新高
            if current_price > self.state.swing_high:
                if self.state.swing_high > 0:
                    self.state.previous_high = self.state.swing_high
                self.state.swing_high = current_price
                self.state.swing_low = 0
                self.state.confirmed = False

            # 2. 确认继续涨：再次超过前高
            if self.state.previous_high > 0 and current_price > self.state.previous_high:
                self.state.confirmed = True

            # 3. 回调时：确认后，只在首次回调时设置 TTP
            if self.state.confirmed and current_price < self.state.swing_high and current_price > entry_price:
                # 只有当还未设置过 TTP 时才设置
                if not self.state.active:
                    if self.state.swing_low == 0 or current_price < self.state.swing_low:
                        self.state.swing_low = current_price
                        self.state.ttp_level = self.state.swing_low - pips
                        self.state.active = True
                # 如果已经设置过 TTP，就不再更新（让 TTP 固定在那里等待触发）

        elif position_side == "SHORT":
            # 空头：需要先有浮盈才能追踪
            profit_pct = (entry_price - current_price) / entry_price
            if profit_pct < self.config.ttp_trigger_pct:
                return  # 浮盈不足

            # 1. 创新低
            if current_price < self.state.swing_low or self.state.swing_low == 0:
                if self.state.swing_low > 0:
                    self.state.previous_low = self.state.swing_low
                self.state.swing_low = current_price
                self.state.swing_high = 0
                self.state.confirmed = False

            # 2. 确认继续跌：再次低于前低
            if self.state.previous_low > 0 and current_price < self.state.previous_low:
                self.state.confirmed = True

            # 3. 反弹时：确认后，只在首次设置 TTP
            if self.state.confirmed and current_price > self.state.swing_low and current_price < entry_price:
                if not self.state.active:
                    if self.state.swing_high == 0 or current_price > self.state.swing_high:
                        self.state.swing_high = current_price
                        self.state.ttp_level = self.state.swing_high + pips
                        self.state.active = True

    def _check_ttp_trigger(
        self,
        current_price: float,
        position_side: str
    ) -> RiskCheckResult:
        """检查是否触发 TTP"""
        if not self.state.active or self.state.ttp_level <= 0:
            return RiskCheckResult()

        if position_side == "LONG":
            # 多头：价格跌破 TTP
            if current_price <= self.state.ttp_level:
                return RiskCheckResult(
                    should_close=True,
                    reason="TTP",
                    confidence=1.0,
                    ttp_level=self.state.ttp_level,
                )

        elif position_side == "SHORT":
            # 空头：价格涨过 TTP
            if current_price >= self.state.ttp_level:
                return RiskCheckResult(
                    should_close=True,
                    reason="TTP",
                    confidence=1.0,
                    ttp_level=self.state.ttp_level,
                )

        return RiskCheckResult()

    def __repr__(self) -> str:
        """字符串表示"""
        status = "活跃" if self.state.active else "未激活"
        return (
            f"<TTPManager: "
            f"状态={status}, "
            f"触发={self.config.ttp_trigger_pct*100:.1f}%, "
            f"缓冲={self.config.ttp_buffer_pips:.1f}pips>"
        )
