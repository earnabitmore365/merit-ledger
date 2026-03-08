#!/usr/bin/env python3
"""
Trading System

交易系统主控
整合策略、风险管理、交易所适配器
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from core.strategy.base import Strategy, Signal
from core.risk.base import RiskManager, RiskCheckResult
from exchange.base import ExchangeAdapter, OrderRequest, OrderSide, OrderType


# ==================== 日志配置 ====================

def setup_logger(name: str = "trading") -> logging.Logger:
    """设置日志
    
    Args:
        name: 日志名称
    
    Returns:
        Logger: 日志实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 控制台处理器
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger


# ==================== 交易系统主控 ====================

class TradingSystem:
    """交易系统主控
    
    整合策略、风险管理、交易所适配器
    实现完整的自动交易逻辑
    
    Usage:
        # 创建交易所适配器
        adapter = HyperLiquidAdapter(config)
        
        # 创建策略
        strategy = VWAPStrategy()
        
        # 创建风险管理
        risk_mgr = StopLossManager()
        
        # 创建交易系统
        system = TradingSystem(
            exchange=adapter,
            strategy=strategy,
            risk_manager=risk_mgr,
        )
        
        # 运行
        system.run()
    """
    
    def __init__(
        self,
        exchange: ExchangeAdapter,
        strategy: Strategy,
        risk_manager: RiskManager = None,
        config: Dict = None
    ):
        """初始化
        
        Args:
            exchange: 交易所适配器
            strategy: 策略
            risk_manager: 风险管理（可选）
            config: 附加配置
        """
        self.exchange = exchange
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.config = config or {}
        
        # 状态
        self.position = None
        self.entry_price = 0.0
        self.running = False
        
        # 日志
        self.logger = setup_logger("TradingSystem")
    
    # ==================== 核心方法 ====================
    
    def run(self, interval_seconds: int = 60, max_iterations: int = None):
        """运行交易系统
        
        Args:
            interval_seconds: 执行间隔（秒）
            max_iterations: 最大执行次数（None=无限）
        """
        self.running = True
        self.logger.info("=" * 50)
        self.logger.info("交易系统启动")
        self.logger.info(f"交易所: {self.exchange.get_exchange_name()}")
        self.logger.info(f"策略: {self.strategy.name}")
        self.logger.info(f"币种: {self.config.get('coin', 'ETH')}")
        self.logger.info("=" * 50)
        
        try:
            iteration = 0
            while self.running:
                iteration += 1
                
                # 检查是否达到最大次数
                if max_iterations and iteration > max_iterations:
                    self.logger.info(f"达到最大执行次数: {max_iterations}")
                    break
                
                self.run_once()
                
                # 休眠
                self._sleep(interval_seconds)
        
        except KeyboardInterrupt:
            self.logger.info("收到停止信号 (Ctrl+C)")
        finally:
            self.stop()
    
    def run_once(self) -> Dict:
        """执行一次交易检查
        
        Returns:
            Dict: 执行结果
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'signal': None,
            'action': None,
            'position': self.position,
            'entry_price': self.entry_price,
        }
        
        try:
            coin = self.config.get('coin', 'ETH')
            
            # 1. 获取 K 线数据
            klines = self._get_klines()
            if not klines:
                self.logger.warning("无法获取 K 线数据")
                return result
            
            # 2. 生成信号
            signal = self._generate_signal(klines)
            result['signal'] = signal.value
            
            # 3. 同步持仓状态
            self._sync_position()
            
            # 4. 风险管理检查
            risk_result = None
            if self.position and self.risk_manager:
                risk_result = self._check_risk()
                if risk_result.should_close:
                    self._close_position(risk_result.reason)
                    result['action'] = risk_result.reason
                    self.logger.info(f"[{result['timestamp']}] {result['action']} | 持仓: {result['position']}")
                    return result
            
            # 5. 执行交易
            if signal == Signal.BUY and not self.position:
                self._open_position("BUY")
                result['action'] = "OPEN_LONG"
                self.logger.info(f"[{result['timestamp']}] {result['action']} | 信号: {signal.value}")
            
            elif signal == Signal.SELL and not self.position:
                self._open_position("SELL")
                result['action'] = "OPEN_SHORT"
                self.logger.info(f"[{result['timestamp']}] {result['action']} | 信号: {signal.value}")
            
            else:
                self.logger.debug(f"[{result['timestamp']}] 持仓: {self.position} | 信号: {signal.value}")
        
        except Exception as e:
            self.logger.error(f"执行错误: {e}", exc_info=True)
        
        return result
    
    def stop(self):
        """停止交易系统"""
        self.running = False
        self.logger.info("交易系统已停止")
        self.logger.info("=" * 50)
    
    # ==================== 配置方法 ====================
    
    def set_coin(self, coin: str):
        """设置交易币种
        
        Args:
            coin: 币种名称
        """
        self.config['coin'] = coin.upper()
        self.logger.info(f"设置交易币种: {self.config['coin']}")
    
    def set_leverage(self, leverage: float):
        """设置杠杆
        
        Args:
            leverage: 杠杆倍数
        """
        self.config['leverage'] = leverage
        self.logger.info(f"设置杠杆: {leverage}x")
    
    def set_position_pct(self, pct: float):
        """设置仓位比例
        
        Args:
            pct: 仓位比例 (0.1 = 10%)
        """
        self.config['position_pct'] = pct
        self.logger.info(f"设置仓位: {pct*100:.0f}%")
    
    # ==================== 状态查询 ====================
    
    def get_status(self) -> Dict:
        """获取当前状态
        
        Returns:
            Dict: 系统状态
        """
        return {
            'running': self.running,
            'position': self.position,
            'entry_price': self.entry_price,
            'strategy': self.strategy.name,
            'coin': self.config.get('coin', 'ETH'),
            'leverage': self.config.get('leverage', 10.0),
        }
    
    def get_position_info(self) -> Dict:
        """获取持仓信息
        
        Returns:
            Dict: 持仓信息
        """
        if not self.position:
            return {'has_position': False}
        
        coin = self.config.get('coin', 'ETH')
        current_price = self.exchange.get_price(coin)
        
        if self.position == "BUY":
            pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
        else:
            pnl_pct = (self.entry_price - current_price) / self.entry_price * 100
        
        return {
            'has_position': True,
            'coin': coin,
            'side': self.position,
            'entry_price': self.entry_price,
            'current_price': current_price,
            'pnl_pct': pnl_pct,
        }
    
    # ==================== 私有方法 ====================
    
    def _get_klines(self) -> List[Dict]:
        """获取 K 线数据"""
        coin = self.config.get('coin', 'ETH')
        interval = self.config.get('interval', '1h')
        limit = self.config.get('kline_limit', 100)
        return self.exchange.get_klines(coin, interval, limit)
    
    def _generate_signal(self, klines: List[Dict]) -> Signal:
        """生成信号"""
        coin = self.config.get('coin', 'ETH')
        return self.strategy.generate_signal(coin, klines)
    
    def _sync_position(self):
        """同步持仓状态"""
        coin = self.config.get('coin', 'ETH')
        positions = self.exchange.get_positions()
        
        if positions:
            pos = positions[0]
            if pos['side'] == "LONG":
                self.position = "BUY"
            elif pos['side'] == "SHORT":
                self.position = "SELL"
            self.entry_price = pos.get('entry_price', 0.0)
        else:
            self.position = None
    
    def _check_risk(self) -> RiskCheckResult:
        """风险管理检查"""
        coin = self.config.get('coin', 'ETH')
        position = self.exchange.get_position(coin)
        current_price = self.exchange.get_price(coin)
        
        return self.risk_manager.check(
            position,
            current_price,
            position_side=self.position,
            entry_price=self.entry_price,
        )
    
    def _open_position(self, side: str):
        """开仓"""
        coin = self.config.get('coin', 'ETH')
        balance = self.exchange.get_balance().get('usdc', 0)
        
        # 计算仓位
        position_pct = self.config.get('position_pct', 0.1)
        trade_capital = balance * position_pct
        leverage = self.config.get('leverage', 10.0)
        current_price = self.exchange.get_price(coin)
        size = (trade_capital * leverage) / current_price
        
        # 下单
        order = OrderRequest(
            coin=coin,
            side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            size=size,
        )
        result = self.exchange.place_order(order)
        
        if result.success:
            self.position = side
            self.entry_price = current_price
            self.logger.info(
                f"开仓: {side} {coin} @ ${current_price:.2f} "
                f"数量: {size:.4f}"
            )
        else:
            self.logger.error(f"开仓失败: {result.message}")
    
    def _close_position(self, reason: str = "CLOSE"):
        """平仓"""
        if not self.position:
            return
        
        coin = self.config.get('coin', 'ETH')
        result = self.exchange.close_position(coin)
        
        if result.success:
            self.position = None
            self.logger.info(f"平仓: {reason} {coin}")
        else:
            self.logger.error(f"平仓失败: {result.message}")
    
    def _sleep(self, seconds: int):
        """休眠"""
        import time
        time.sleep(seconds)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<TradingSystem: "
            f"{self.exchange.get_exchange_name() if hasattr(self.exchange, 'get_exchange_name') else 'Exchange'}, "
            f"{self.strategy.name}, "
            f"{self.config.get('coin', 'ETH')}>"
        )


# ==================== 主程序 ====================

def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Abby Auto Trading System')
    parser.add_argument('--coin', type=str, default='ETH', help='交易币种')
    parser.add_argument('--strategy', type=str, default='vwap', help='策略名称')
    parser.add_argument('--interval', type=int, default=60, help='执行间隔（秒）')
    args = parser.parse_args()
    
    # 这里应该是完整的初始化逻辑
    print(f"启动交易系统: {args.coin} / {args.strategy}")


if __name__ == "__main__":
    main()
