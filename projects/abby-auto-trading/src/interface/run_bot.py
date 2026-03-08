#!/usr/bin/env python3
"""
Abby Trading Bot - 简化版

支持多空双向交易，和回测系统保持一致
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加 src 路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.strategy import get_strategy
from core.risk import TTPManager, TTPConfig
from exchange.hyperliquid.adapter import HyperLiquidAdapter
from exchange.base import OrderRequest, OrderSide, OrderType
from config.testnet_secrets import HYPERLIQUID_TESTNET
# from core.abby_logging import setup_logging, log_trade, log_signal, log_pnl


class AbbyBot:
    """Abby 交易机器人"""

    def __init__(self, config: dict):
        self.config = config
        self.strategy_name = config.get('strategy', 'ma')
        self.coin = config.get('coin', 'BTC')
        self.interval = config.get('interval', '1h')
        self.mode = config.get('mode', 'paper')
        self.stop_loss_pct = config.get('stop_loss_pct', 0.10)
        self.enable_ttp = config.get('enable_ttp', True)

        # 从 secrets 获取真实交易配置
        exchange_config = {
            'wallet_address': HYPERLIQUID_TESTNET.get('address', ''),
            'private_key': HYPERLIQUID_TESTNET.get('private_key', ''),
            'endpoint': 'https://api.hyperliquid-testnet.xyz',
            'testnet': True
        }

        # 初始化组件
        self.strategy = get_strategy(self.strategy_name)
        self.exchange = HyperLiquidAdapter(exchange_config)
        self.exchange.connect()

        # 初始化 TTP 管理器
        self.ttp_manager = TTPManager(TTPConfig(ttp_enabled=self.enable_ttp, ttp_buffer_pips=5.0))

        self.position = None
        self.entry_price = None
        self.margin = None
        self.position_size = None

        # 设置日志
        import logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
        self.logger = logging.info
        self.signal_log = logging.info
        self.pnl_log = logging.info
        
        # 记录交易
        self.trades = []
        
        self.logger(f"🤖 启动 Abby Bot: {self.strategy_name}/{self.coin}/{self.interval}")

    def run(self):
        """运行机器人"""
        while True:
            try:
                self.step()
                time.sleep(60)
            except KeyboardInterrupt:
                self.logger("\n⏹️ 停止")
                break
            except Exception as e:
                self.logger(f"❌ 错误: {e}")
                time.sleep(5)

    def step(self):
        """单步执行"""
        self.logger("=" * 30 + " 开始执行 step " + "=" * 30)

        # 获取K线
        try:
            klines = self.exchange.get_klines(self.coin, self.interval, limit=100)
            if not klines:
                self.logger("⚠️ 没有获取到 K 线数据")
                return
        except Exception as e:
            self.logger(f"❌ 获取K线失败: {e}")
            return

        current_price = klines[-1]['close']
        self.logger(f"📊 当前价格: ${current_price}")

        # 显示仓位信息
        self._log_position_info(current_price)

        # 1. 检查止损
        if self.position == 'BUY':
            price_change = (current_price - self.entry_price) / self.entry_price
            if price_change <= -self.stop_loss_pct:
                self.logger(f"🛑 触发止损 BUY @ ${current_price:.2f} ({price_change*100:.2f}%)")
                self._close_buy(current_price)
                self.trades[-1]['side'] = 'STOP_LOSS_BUY'
                self._reset_ttp()
                return

        elif self.position == 'SELL':
            price_change = (self.entry_price - current_price) / self.entry_price
            if price_change <= -self.stop_loss_pct:
                self.logger(f"🛑 触发止损 SELL @ ${current_price:.2f} ({price_change*100:.2f}%)")
                self._close_sell(current_price)
                self.trades[-1]['side'] = 'STOP_LOSS_SELL'
                self._reset_ttp()
                return

        # 2. 检查TTP（移动止盈）
        if self.enable_ttp and self.position == 'BUY' and self.entry_price:
            self._check_ttp_buy(current_price)
        elif self.enable_ttp and self.position == 'SELL' and self.entry_price:
            self._check_ttp_sell(current_price)

        # 如果TTP触发了平仓，直接返回
        if self.position is None:
            # 没有持仓，生成信号尝试开仓
            pass
        else:
            # 有持仓，检查是否需要反手
            pass

        # 3. 生成信号
        signal = self.strategy.generate_signal(self.coin, klines)

        # 调试：显示所有信号
        self.logger(f"🔍 信号: {signal.name} | 置信度: {signal.confidence}")

        if signal.name == "HOLD":
            return
        
        # 4. 执行交易 - 和回测系统一致
        self.signal_log(f"信号: {signal.name} | {self.coin} | ${current_price:.2f}")
        
        if signal.name == "BUY":
            if self.position is None:
                self._buy(current_price)
            elif self.position == 'SELL':
                self._close_sell_and_buy(current_price)
        elif signal.name == "SELL":
            if self.position is None:
                self._sell(current_price)
            elif self.position == 'BUY':
                self._close_buy_and_sell(current_price)

    def _log_position_info(self, current_price):
        """显示仓位信息：保证金、PNL、持仓总额"""
        if self.position is None or self.margin is None or self.position_size is None:
            return
        
        if self.position == 'BUY':
            position_value = self.position_size * current_price
        else:  # SELL
            position_value = self.position_size * current_price
        
        pnl = position_value - self.margin
        
        self.logger(f"📊 仓位信息 | 保证金: {self.margin:.2f} USDT | PNL: {pnl:+.2f} USDT | 持仓总额: {position_value:.2f} USDT")

    def _reset_ttp(self):
        """重置TTP追踪变量"""
        self.high_since_entry = None
        self.previous_high = None
        self.swing_low = None
        self.ttp_level = None

    def _check_ttp_buy(self, current_price):
        """检查 BUY 持仓的 TTP - 使用统一的 TTP 管理器"""
        if not self.enable_ttp or not self.position:
            return

        # 构建持仓信息
        position = {
            'coin': self.coin,
            'side': 'LONG',
            'entry_price': self.entry_price
        }

        # 调用 TTP 管理器
        result = self.ttp_manager.check(
            position=position,
            current_price=current_price,
            entry_price=self.entry_price,
            position_side='LONG'
        )

        # 检查是否触发 TTP
        if result.should_close:
            self.logger(f"🚀 触发 TTP BUY @ ${current_price:.2f}")
            self._close_buy(current_price)
            self.trades[-1]['side'] = 'TTP_BUY'
            self.ttp_manager.reset()

    def _check_ttp_sell(self, current_price):
        """检查 SELL 持仓的 TTP - 使用统一的 TTP 管理器"""
        if not self.enable_ttp or not self.position:
            return

        # 调试：显示 TTP 状态
        self.logger(f"📊 TTP状态: {self.ttp_manager}")

        # 构建持仓信息
        position = {
            'coin': self.coin,
            'side': 'SHORT',
            'entry_price': self.entry_price
        }

        # 调用 TTP 管理器
        result = self.ttp_manager.check(
            position=position,
            current_price=current_price,
            entry_price=self.entry_price,
            position_side='SHORT'
        )

        # 调试：显示结果
        if result.should_close:
            self.logger(f"🚀 触发 TTP SELL @ ${current_price:.2f}")
            self._close_sell(current_price)
            self.trades[-1]['side'] = 'TTP_SELL'
            self.ttp_manager.reset()

    def _buy(self, price):
        """BUY: 开多"""
        self.logger(f"🟢 BUY {self.coin} @ ${price:.2f}")
        
        # 计算仓位大小
        balance = self.exchange.get_balance().get('USDT', 0)
        margin = balance * 0.10  # 10%保证金（至少100）
        if margin < 100:
            margin = 100
        
        position_value = margin * 10  # 10倍杠杆
        size = position_value / price  # 仓位大小
        
        order = OrderRequest(
            coin=self.coin,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=round(size, 4)
        )
        
        result = self.exchange.place_order(order)
        
        if result.success:
            self.position = 'BUY'
            self.entry_price = price
            self.margin = margin  # 记录保证金
            self.position_size = size  # 记录仓位大小
            self.trades.append({
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.now().strftime("%H:%M:%S"),
                'coin': self.coin,
                'side': 'BUY',
                'price': price,
                'margin': margin,
                'pnl': 0
            })
            self.logger(f"✅ BUY成功 | 保证金: {margin:.2f} USDT | 仓位: {size:.4f} {self.coin}")

    def _sell(self, price):
        """SELL: 开空"""
        self.logger(f"🔴 SELL {self.coin} @ ${price:.2f}")
        
        # 计算仓位大小
        balance = self.exchange.get_balance().get('USDT', 0)
        margin = balance * 0.10  # 10%保证金（至少100）
        if margin < 100:
            margin = 100
        
        position_value = margin * 10  # 10倍杠杆
        size = position_value / price  # 仓位大小
        
        order = OrderRequest(
            coin=self.coin,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            size=round(size, 4)
        )
        
        result = self.exchange.place_order(order)
        
        if result.success:
            self.position = 'SELL'
            self.entry_price = price
            self.margin = margin  # 记录保证金
            self.position_size = size  # 记录仓位大小
            self.trades.append({
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.now().strftime("%H:%M:%S"),
                'coin': self.coin,
                'side': 'SELL',
                'price': price,
                'margin': margin,
                'pnl': 0
            })
            self.logger(f"✅ SELL成功 | 保证金: {margin:.2f} USDT | 仓位: {size:.4f} {self.coin}")

    def _close_buy(self, price):
        """CLOSE_BUY: 平多"""
        self.logger(f"🔴 CLOSE_BUY {self.coin} @ ${price:.2f}")
        
        order = OrderRequest(
            coin=self.coin,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            size=1.0
        )
        
        result = self.exchange.place_order(order)
        
        if result.success:
            self.trades.append({
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.now().strftime("%H:%M:%S"),
                'coin': self.coin,
                'side': 'CLOSE_BUY',
                'price': price,
                'pnl': 0
            })
            self.position = None
            self.entry_price = None
            self.logger(f"✅ CLOSE_BUY成功")

    def _close_sell(self, price):
        """CLOSE_SELL: 平空"""
        self.logger(f"🟢 CLOSE_SELL {self.coin} @ ${price:.2f}")
        
        order = OrderRequest(
            coin=self.coin,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=1.0
        )
        
        result = self.exchange.place_order(order)
        
        if result.success:
            self.trades.append({
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.now().strftime("%H:%M:%S"),
                'coin': self.coin,
                'side': 'CLOSE_SELL',
                'price': price,
                'pnl': 0
            })
            self.position = None
            self.entry_price = None
            self.logger(f"✅ CLOSE_SELL成功")

    def _close_buy_and_sell(self, price):
        """平多 + 开空 (反手)"""
        self.logger(f"🔄 CLOSE_BUY -> SELL {self.coin} @ ${price:.2f}")
        
        # 平多
        self._close_buy(price)
        # 开空
        self._sell(price)
        # 重置TTP
        self._reset_ttp()

    def _close_sell_and_buy(self, price):
        """平空 + 开多 (反手)"""
        self.logger(f"🔄 CLOSE_SELL -> BUY {self.coin} @ ${price:.2f}")
        
        # 平空
        self._close_sell(price)
        # 开多
        self._buy(price)
        # 重置TTP
        self._reset_ttp()


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', '-s', default='ma')
    parser.add_argument('--coin', '-c', default='BTC')
    parser.add_argument('--interval', '-i', default='1h')
    parser.add_argument('--mode', '-m', default='paper')
    args = parser.parse_args()
    
    bot = AbbyBot({
        'strategy': args.strategy,
        'coin': args.coin,
        'interval': args.interval,
        'mode': args.mode,
        'wallet_address': HYPERLIQUID_TESTNET['address'],
        'private_key': HYPERLIQUID_TESTNET['private_key'],
    })
    bot.run()


if __name__ == "__main__":
    main()
