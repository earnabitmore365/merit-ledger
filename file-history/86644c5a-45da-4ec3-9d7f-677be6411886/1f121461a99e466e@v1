#!/usr/bin/env python3
"""
HyperLiquid WebSocket

HyperLiquid WebSocket 客户端
实时获取价格更新
"""

import json
import logging
import threading
from typing import Callable, Dict, Optional


class HyperLiquidWebSocket:
    """HyperLiquid WebSocket 客户端
    
    Usage:
        # 回调方式
        def on_message(data):
            print(data)
        
        ws = HyperLiquidWebSocket(
            endpoint="wss://api.hyperliquid-testnet.xyz/ws",
            on_message=on_message,
        )
        ws.connect()
        
        # 订阅价格
        ws.subscribe("BTC")
        ws.subscribe("ETH")
    
    Attributes:
        connected: 是否已连接
        prices: 最新价格缓存
    """
    
    def __init__(
        self,
        endpoint: str,
        on_message: Callable[[dict], None] = None,
    ):
        """初始化
        
        Args:
            endpoint: WebSocket 端点
            on_message: 消息回调函数
        """
        self.endpoint = endpoint
        self.on_message = on_message
        
        # 连接状态
        self.connected = False
        self.ws = None
        self._thread = None
        
        # 价格缓存
        self.prices: Dict[str, float] = {}
        
        # 日志
        self.logger = logging.getLogger("HyperLiquidWebSocket")
    
    # ==================== 连接管理 ====================
    
    def connect(self) -> bool:
        """连接 WebSocket

        Returns:
            bool: 是否连接成功
        """
        try:
            import websockets
            import asyncio

            # 使用异步连接
            async def _connect():
                self.ws = await websockets.connect(self.endpoint)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_connect())

            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

            self.connected = True
            self.logger.info(f"WebSocket 已连接: {self.endpoint}")
            return True

        except Exception as e:
            self.logger.error(f"WebSocket 连接失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self.logger.info("WebSocket 已断开")
    
    # ==================== 订阅管理 ====================
    
    def subscribe(self, coin: str):
        """订阅币种价格
        
        Args:
            coin: 币种名称（如 "BTC"）
        """
        if not self.connected:
            self.logger.warning("未连接，无法订阅")
            return
        
        # 发送订阅消息
        self._send({
            "method": "subscribe",
            "subscription": {
                "type": "trades",
                "coin": coin,
            }
        })
    
    def unsubscribe(self, coin: str):
        """取消订阅币种
        
        Args:
            coin: 币种名称
        """
        if not self.connected:
            return
        
        self._send({
            "method": "unsubscribe",
            "subscription": {
                "type": "trades",
                "coin": coin,
            }
        })
    
    # ==================== 价格获取 ====================
    
    def get_price(self, coin: str) -> Optional[float]:
        """获取当前价格
        
        Args:
            coin: 币种名称
        
        Returns:
            float: 当前价格，获取失败返回 None
        """
        return self.prices.get(coin)
    
    def get_all_prices(self) -> Dict[str, float]:
        """获取所有订阅币种的价格
        
        Returns:
            Dict[str, float]: 价格字典
        """
        return self.prices.copy()
    
    # ==================== 私有方法 ====================
    
    def _run(self):
        """运行循环"""
        import asyncio
        
        async def connect_loop():
            while self.connected:
                try:
                    async with websockets.connect(self.endpoint) as ws:
                        # 重新订阅
                        for coin in list(self.prices.keys()):
                            ws.send(json.dumps({
                                "method": "subscribe",
                                "subscription": {
                                    "type": "trades",
                                    "coin": coin,
                                }
                            }))
                        
                        # 接收消息
                        async for message in ws:
                            self._handle_message(message)
                            
                except Exception as e:
                    if self.connected:
                        self.logger.warning(f"WebSocket 断开，5秒后重连...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(connect_loop())
        except Exception as e:
            self.logger.error(f"WebSocket 循环错误: {e}")
    
    def _handle_message(self, message: str):
        """处理消息
        
        Args:
            message: WebSocket 消息
        """
        try:
            data = json.loads(message)
            
            # 解析交易数据
            if "data" in data:
                trades = data["data"]
                for trade in trades:
                    coin = trade.get("coin")
                    price = trade.get("px")
                    
                    if coin and price:
                        self.prices[coin] = float(price) / 1000000  # 价格需要除以 1000000
            
            # 调用回调
            if self.on_message:
                self.on_message(data)
                
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
    
    def _send(self, message: dict):
        """发送消息
        
        Args:
            message: 消息字典
        """
        if self.connected and self.ws:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.ws.send(json.dumps(message)))
            except Exception as e:
                self.logger.error(f"发送消息失败: {e}")
    
    # ==================== 属性 ====================
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self.connected
    
    def __repr__(self) -> str:
        """字符串表示"""
        status = "已连接" if self.connected else "未连接"
        return f"<HyperLiquidWebSocket: {status}>"


# ==================== 工厂函数 ====================

def create_websocket(
    testnet: bool = True,
    on_message: Callable[[dict], None] = None,
) -> HyperLiquidWebSocket:
    """创建 WebSocket 实例
    
    Args:
        testnet: 是否使用测试网
        on_message: 消息回调
    
    Returns:
        HyperLiquidWebSocket: WebSocket 实例
    """
    endpoint = (
        "wss://api.hyperliquid-testnet.xyz/ws" if testnet
        else "wss://api.hyperliquid.xyz/ws"
    )
    
    return HyperLiquidWebSocket(
        endpoint=endpoint,
        on_message=on_message,
    )
