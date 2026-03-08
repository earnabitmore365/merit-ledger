#!/usr/bin/env python3
"""
TTP Manager

移动止盈管理器
根据价格波动自动调整止盈价位
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

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
    ttp_trigger_pct: float = 0.02  # 2% 浮盈后启动


# ==================== 状态类定义 ====================

@dataclass
class TTPState:
    """TTP 状态"""
    active: bool = False  # TTP 是否激活
    swing_high: float = 0.0  # 多头：回调高点
    swing_low: float = 0.0   # 空头：回调低点
    ttp_level: float = 0.0   # TTP 触发价位
    entry_price: float = 0.0  # 开仓价格
    position_side: str = ""    # 持仓方向
    
    def reset(self):
        """重置状态"""
        self.active = False
        self.swing_high = 0.0
        self.swing_low = 0.0
        self.ttp_level = 0.0
        self.entry_price = 0.0
        self.position_side = ""


# ==================== 移动止盈管理器 ====================

class TTPManager(RiskManager):
    """移动止盈管理器
    
    实现移动止盈（Trailing Take Profit）逻辑：
    1. 价格向有利方向波动后回调
    2. 回调形成新的支撑/阻力位
    3. 价格反向突破 TTP 价位时平仓
    
    Usage:
        config = TTPConfig(ttp_enabled=True, ttp_buffer_pips=5.0)
        manager = TTPManager(config)
        
        result = manager.check(position, current_price)
    """
    
    def __init__(self, config: TTPConfig = None):
        """初始化
        
        Args:
            config: 移动止盈配置
        """
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
        """检查是否触发移动止盈
        
        Args:
            position: 持仓信息
            current_price: 当前价格
            entry_price: 开仓价格（可选）
            position_side: 持仓方向（可选）
            **kwargs: 附加参数
        
        Returns:
            RiskCheckResult: 检查结果
        """
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
        
        # 检查是否满足启动条件
        if profit_pct < self.config.ttp_trigger_pct:
            # 浮盈不足，重置状态
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
        
        Args:
            position_side: 持仓方向
            entry_price: 开仓价格
            current_price: 当前价格
        """
        # 如果是新的持仓，重置状态
        if self.state.position_side != position_side or self.state.entry_price != entry_price:
            self.state.reset()
            self.state.position_side = position_side
            self.state.entry_price = entry_price
        
        # 计算 pips
        pips = entry_price * self.config.ttp_buffer_pips * 0.0001
        
        if position_side == "LONG":
            # 多头：创新高后回调更新 swing_low
            if self.state.swing_high == 0 or current_price > self.state.swing_high:
                self.state.swing_high = current_price
                # 新高后回调才更新 swing_low
            elif current_price < self.state.swing_high and current_price > entry_price:
                # 更新回调低点
                if self.state.swing_low == 0 or current_price < self.state.swing_low:
                    self.state.swing_low = current_price
                    # 设置 TTP
                    self.state.ttp_level = self.state.swing_low - pips
                    self.state.active = True
        
        elif position_side == "SHORT":
            # 空头：创新低后反弹更新 swing_high
            if self.state.swing_low == 0 or current_price < self.state.swing_low:
                self.state.swing_low = current_price
                # 新低后反弹才更新 swing_high
            elif current_price > self.state.swing_low and current_price < entry_price:
                # 更新反弹高点
                if self.state.swing_high == 0 or current_price > self.state.swing_high:
                    self.state.swing_high = current_price
                    # 设置 TTP
                    self.state.ttp_level = self.state.swing_high + pips
                    self.state.active = True
    
    def _check_ttp_trigger(
        self,
        current_price: float,
        position_side: str
    ) -> RiskCheckResult:
        """检查是否触发 TTP
        
        Args:
            current_price: 当前价格
            position_side: 持仓方向
        
        Returns:
            RiskCheckResult: 检查结果
        """
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
