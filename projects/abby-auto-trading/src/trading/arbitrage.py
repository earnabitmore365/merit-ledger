#!/usr/bin/env python3
"""
Arbitrage System

套利系统
跨交易所寻找套利机会并执行
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from exchange.base import ExchangeAdapter


# ==================== 配置 ====================

@dataclass
class ArbitrageConfig:
    """套利配置
    
    Attributes:
        min_spread_pct: 最小价差百分比（套利机会）
        min_profit_pct: 最小利润百分比（扣除手续费后）
        check_interval: 检查间隔（秒）
        auto_execute: 是否自动执行
        max_position_pct: 最大仓位比例
    """
    min_spread_pct: float = 0.5  # 0.5% 价差
    min_profit_pct: float = 0.2   # 0.2% 利润
    check_interval: int = 5         # 每 5 秒检查
    auto_execute: bool = False     # 默认不自动执行
    max_position_pct: float = 0.5   # 最大 50% 仓位


# ==================== 套利结果 ====================

@dataclass
class ArbitrageResult:
    """套利结果
    
    Attributes:
        opportunity: 是否有套利机会
        buy_exchange: 低价交易所
        sell_exchange: 高价交易所
        buy_price: 买入价格
        sell_price: 卖出价格
        spread_pct: 价差百分比
        profit_pct: 预估利润
        coin: 币种
    """
    opportunity: bool
    coin: str = ""
    buy_exchange: str = ""
    sell_exchange: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    spread_pct: float = 0.0
    profit_pct: float = 0.0
    message: str = ""


# ==================== 套利系统 ====================

class ArbitrageSystem:
    """套利系统
    
    跨交易所寻找套利机会并执行
    
    Usage:
        # 创建交易所列表
        exchanges = {
            'hl': HyperLiquidAdapter(config1),
            'binance': BinanceAdapter(config2),
        }
        
        # 创建套利系统
        arb = ArbitrageSystem(exchanges)
        
        # 检查套利机会
        result = arb.check_opportunity('ETH')
        
        if result.opportunity:
            arb.execute(result)
    """
    
    def __init__(
        self,
        exchanges: Dict[str, ExchangeAdapter],
        config: ArbitrageConfig = None
    ):
        """初始化
        
        Args:
            exchanges: 交易所字典 {名称: 适配器}
            config: 套利配置
        """
        self.exchanges = exchanges
        self.config = config or ArbitrageConfig()
        self.logger = logging.getLogger("Arbitrage")
        
        # 缓存价格
        self._price_cache = {}
    
    # ==================== 核心方法 ====================
    
    def check_all_coins(self, coins: List[str]) -> List[ArbitrageResult]:
        """检查所有币种的套利机会
        
        Args:
            coins: 币种列表
        
        Returns:
            List[ArbitrageResult]: 套利机会列表
        """
        results = []
        
        for coin in coins:
            result = self.check_opportunity(coin)
            if result.opportunity:
                results.append(result)
        
        return results
    
    def check_opportunity(self, coin: str) -> ArbitrageResult:
        """检查单个币种的套利机会
        
        Args:
            coin: 币种名称
        
        Returns:
            ArbitrageResult: 套利检查结果
        """
        # 获取所有交易所的价格
        prices = self._get_all_prices(coin)
        
        if len(prices) < 2:
            return ArbitrageResult(
                opportunity=False,
                coin=coin,
                message="交易所数量不足",
            )
        
        # 找出最低价和最高价
        sorted_prices = sorted(prices.items(), key=lambda x: x[1])
        
        buy_exchange, buy_price = sorted_prices[0]  # 最低价
        sell_exchange, sell_price = sorted_prices[-1]  # 最高价
        
        # 计算价差
        spread_pct = (sell_price - buy_price) / buy_price * 100
        
        # 检查是否满足套利条件
        if spread_pct < self.config.min_spread_pct:
            return ArbitrageResult(
                opportunity=False,
                coin=coin,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread_pct=spread_pct,
                message=f"价差 {spread_pct:.2f}% 小于最小要求 {self.config.min_spread_pct}%",
            )
        
        # 计算预估利润（扣除手续费）
        fee_pct = 0.1  # 假设 0.1% 手续费
        profit_pct = spread_pct - fee_pct * 2
        
        if profit_pct < self.config.min_profit_pct:
            return ArbitrageResult(
                opportunity=False,
                coin=coin,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                spread_pct=spread_pct,
                profit_pct=profit_pct,
                message=f"预估利润 {profit_pct:.2f}% 小于最小要求 {self.config.min_profit_pct}%",
            )
        
        return ArbitrageResult(
            opportunity=True,
            coin=coin,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_pct=spread_pct,
            profit_pct=profit_pct,
            message=f"套利机会: {buy_exchange} @ ${buy_price:.2f} → {sell_exchange} @ ${sell_price:.2f}",
        )
    
    def execute(self, result: ArbitrageResult) -> Dict:
        """执行套利
        
        Args:
            result: 套利结果
        
        Returns:
            Dict: 执行结果
        """
        if not result.opportunity:
            return {'success': False, 'message': '无套利机会'}
        
        # 检查配置
        if not self.config.auto_execute:
            return {
                'success': False,
                'message': '自动执行已关闭，请手动执行',
                'result': result,
            }
        
        # 执行套利
        buy_exchange = self.exchanges[result.buy_exchange]
        sell_exchange = self.exchanges[result.sell_exchange]
        
        # 1. 在低价交易所买入
        balance = buy_exchange.get_balance().get('usdc', 0)
        position_pct = self.config.max_position_pct
        trade_capital = balance * position_pct
        size = (trade_capital * 10) / result.buy_price  # 10x 杠杆
        
        buy_result = buy_exchange.place_order(
            coin=result.coin,
            side='BUY',
            size=size,
        )
        
        if not buy_result.success:
            return {
                'success': False,
                'message': f'买入失败: {buy_result.message}',
            }
        
        # 2. 在高价交易所卖出
        sell_result = sell_exchange.place_order(
            coin=result.coin,
            side='SELL',
            size=size,
        )
        
        if not sell_result.success:
            return {
                'success': False,
                'message': f'买入成功，但卖出失败: {sell_result.message}',
                'buy_result': buy_result,
            }
        
        return {
            'success': True,
            'message': '套利执行成功',
            'buy_exchange': result.buy_exchange,
            'sell_exchange': result.sell_exchange,
            'buy_price': result.buy_price,
            'sell_price': result.sell_price,
            'profit_pct': result.profit_pct,
        }
    
    def run_monitor(self, coins: List[str], duration_seconds: int = 3600):
        """运行监控
        
        Args:
            coins: 监控的币种列表
            duration_seconds: 监控时长（秒）
        """
        import time
        from datetime import datetime, timedelta
        
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        
        self.logger.info(f"开始套利监控，币种: {coins}")
        self.logger.info(f"最小价差: {self.config.min_spread_pct}%")
        self.logger.info(f"预计结束: {end_time}")
        
        iteration = 0
        while datetime.now() < end_time:
            iteration += 1
            
            # 检查所有币种
            opportunities = self.check_all_coins(coins)
            
            if opportunities:
                self.logger.info("=" * 60)
                self.logger.info(f"发现 {len(opportunities)} 个套利机会")
                self.logger.info("=" * 60)
                
                for opp in opportunities:
                    self.logger.info(
                        f"[{opp.coin}] {opp.buy_exchange} @ ${opp.buy_price:.2f} → "
                        f"{opp.sell_exchange} @ ${opp.sell_price:.2f} "
                        f"(价差: {opp.spread_pct:.2f}%, 利润: {opp.profit_pct:.2f}%)"
                    )
            else:
                self.logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 无套利机会")
            
            # 休眠
            time.sleep(self.config.check_interval)
        
        self.logger.info("套利监控结束")
    
    # ==================== 辅助方法 ====================
    
    def _get_all_prices(self, coin: str) -> Dict[str, float]:
        """获取所有交易所的价格
        
        Args:
            coin: 币种名称
        
        Returns:
            Dict[交易所名称, 价格]
        """
        prices = {}
        
        for name, exchange in self.exchanges.items():
            try:
                price = exchange.get_price(coin)
                prices[name] = price
            except Exception as e:
                self.logger.warning(f"获取 {name} 价格失败: {e}")
        
        return prices
    
    def get_price_comparison(self, coin: str) -> List[Dict]:
        """获取价格对比
        
        Args:
            coin: 币种名称
        
        Returns:
            List[Dict]: 价格对比列表
        """
        prices = self._get_all_prices(coin)
        
        result = []
        for name, price in prices.items():
            result.append({
                'exchange': name,
                'price': price,
            })
        
        # 按价格排序
        result.sort(key=lambda x: x['price'])
        
        return result
    
    def list_exchanges(self) -> List[str]:
        """列出所有交易所
        
        Returns:
            List[str]: 交易所名称列表
        """
        return list(self.exchanges.keys())
    
    def add_exchange(self, name: str, exchange: ExchangeAdapter):
        """添加交易所
        
        Args:
            name: 交易所名称
            exchange: 交易所适配器
        """
        self.exchanges[name] = exchange
        self.logger.info(f"添加交易所: {name}")
    
    def remove_exchange(self, name: str):
        """移除交易所
        
        Args:
            name: 交易所名称
        """
        if name in self.exchanges:
            del self.exchanges[name]
            self.logger.info(f"移除交易所: {name}")
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<ArbitrageSystem: "
            f"交易所={list(self.exchanges.keys())}, "
            f"最小价差={self.config.min_spread_pct}%"
        )
