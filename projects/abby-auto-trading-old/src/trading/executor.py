#!/usr/bin/env python3
"""
Order Executor

订单执行器
封装订单操作细节
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

from src.exchange.base import ExchangeAdapter, OrderRequest, OrderSide, OrderType


# ==================== 配置 ====================

@dataclass
class ExecutorConfig:
    """执行器配置
    
    Attributes:
        retry_count: 重试次数
        retry_delay: 重试间隔（秒）
        timeout: 超时时间（秒）
    """
    retry_count: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0


# ==================== 结果类定义 ====================

@dataclass
class ExecutionResult:
    """执行结果
    
    Attributes:
        success: 是否成功
        order_id: 订单ID
        filled_price: 成交价格
        filled_size: 成交数量
        message: 结果消息
    """
    success: bool
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_size: Optional[float] = None
    message: str = ""


# ==================== 订单执行器 ====================

class Executor:
    """订单执行器
    
    封装订单操作细节
    提供简洁的 API 进行交易操作
    
    Usage:
        executor = Executor(exchange)
        
        # 市价买入
        result = executor.buy_market("ETH", 1.0)
        
        # 限价卖出
        result = executor.sell_limit("ETH", 1.0, 2000.0)
    """
    
    def __init__(self, exchange: ExchangeAdapter, config: ExecutorConfig = None):
        """初始化
        
        Args:
            exchange: 交易所适配器
            config: 执行器配置
        """
        self.exchange = exchange
        self.config = config or ExecutorConfig()
        self.logger = logging.getLogger("Executor")
    
    # ==================== 市价单 ====================
    
    def buy_market(self, coin: str, size: float) -> ExecutionResult:
        """市价买入
        
        Args:
            coin: 币种
            size: 数量
        
        Returns:
            ExecutionResult: 执行结果
        """
        order = OrderRequest(
            coin=coin,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=size,
        )
        return self._execute(order)
    
    def sell_market(self, coin: str, size: float) -> ExecutionResult:
        """市价卖出"""
        order = OrderRequest(
            coin=coin,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            size=size,
        )
        return self._execute(order)
    
    # ==================== 限价单 ====================
    
    def buy_limit(self, coin: str, size: float, price: float) -> ExecutionResult:
        """限价买入
        
        Args:
            coin: 币种
            size: 数量
            price: 价格
        
        Returns:
            ExecutionResult: 执行结果
        """
        order = OrderRequest(
            coin=coin,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            size=size,
            price=price,
        )
        return self._execute(order)
    
    def sell_limit(self, coin: str, size: float, price: float) -> ExecutionResult:
        """限价卖出"""
        order = OrderRequest(
            coin=coin,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            size=size,
            price=price,
        )
        return self._execute(order)
    
    # ==================== 仓位操作 ====================
    
    def close_position(self, coin: str) -> ExecutionResult:
        """平仓
        
        Args:
            coin: 币种
        
        Returns:
            ExecutionResult: 执行结果
        """
        result = self.exchange.close_position(coin)
        return ExecutionResult(
            success=result.success,
            order_id=result.order_id,
            filled_price=result.filled_price,
            filled_size=result.filled_size,
            message=result.message,
        )
    
    def reverse_position(self, coin: str) -> ExecutionResult:
        """反手（平仓并开反向）
        
        Args:
            coin: 币种
        
        Returns:
            ExecutionResult: 执行结果
        """
        # 先平仓
        close_result = self.close_position(coin)
        
        if not close_result.success:
            return close_result
        
        # 获取当前价格和方向
        positions = self.exchange.get_positions()
        if not positions:
            return ExecutionResult(success=False, message="无持仓")
        
        pos = positions[0]
        size = abs(pos['size'])
        current_price = self.exchange.get_price(coin)
        
        # 反向开仓
        if pos['side'] == "LONG":
            return self.sell_market(coin, size)
        else:
            return self.buy_market(coin, size)
    
    def get_position_size(self, coin: str) -> float:
        """获取持仓数量
        
        Args:
            coin: 币种
        
        Returns:
            float: 持仓数量（多头为正，空头为负）
        """
        position = self.exchange.get_position(coin)
        if position:
            if position.side == "LONG":
                return position.size
            else:
                return -position.size
        return 0.0
    
    # ==================== 查询操作 ====================
    
    def get_order_status(self, order_id: str) -> Dict:
        """查询订单状态
        
        Args:
            order_id: 订单ID
        
        Returns:
            Dict: 订单状态
        """
        return self.exchange.get_order_status(order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            bool: 是否成功
        """
        return self.exchange.cancel_order(order_id)
    
    # ==================== 私有方法 ====================
    
    def _execute(self, order: OrderRequest) -> ExecutionResult:
        """执行订单
        
        Args:
            order: 订单请求
        
        Returns:
            ExecutionResult: 执行结果
        """
        result = self.exchange.place_order(order)
        
        # 记录日志
        if result.success:
            self.logger.info(
                f"订单成交: {order.side.value} {order.coin} "
                f"@{result.filled_price} ({result.message})"
            )
        else:
            self.logger.error(
                f"订单失败: {order.side.value} {order.coin} "
                f"({result.message})"
            )
        
        return ExecutionResult(
            success=result.success,
            order_id=result.order_id,
            filled_price=result.filled_price,
            filled_size=result.filled_size,
            message=result.message,
        )
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<Executor: {self.exchange.get_exchange_name() if hasattr(self.exchange, 'get_exchange_name') else 'Exchange'}>"
