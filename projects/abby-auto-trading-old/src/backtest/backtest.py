#!/usr/bin/env python3
"""
Backtest System with Trailing Take Profit (TTP)
=================================================
abby-auto-trading 版本

核心功能：
1. 信号反转时反手（平旧开新）
2. 移动止盈（攻守兼备）- VWAP TTP
3. 爆仓检测
4. 完整的风险指标（夏普、索提诺、卡玛）
5. 5年历史数据回测
"""

import sys
import json
import logging
import statistics
import os
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
from enum import Enum

# 项目根目录 - 根据当前文件位置自动计算
_current_file = os.path.abspath(__file__)
_src_dir = os.path.dirname(_current_file)  # backtest/
_backtest_dir = os.path.dirname(_src_dir)  # src/
PROJECT_ROOT = os.path.dirname(_backtest_dir)  # abby-auto-trading/

DATA_DIR = os.path.join(PROJECT_ROOT, 'src', 'backtest', 'data')
REPORT_DIR = os.path.join(PROJECT_ROOT, 'src', 'backtest', 'reports')

# 添加项目路径
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
src_dir = os.path.join(PROJECT_ROOT, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.strategy import get_strategy
from core.strategy.base import Signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易记录"""
    time: str
    order_type: str  # BUY, SELL, CLOSE_BUY, CLOSE_SELL, TTP_BUY, TTP_SELL, LIQUIDATION
    price: float
    capital: float
    pnl: float
    balance: float  # 该笔交易后的余额
    withdraw: float = 0  # 提款金额（默认0）


@dataclass
class BacktestResult:
    """回测结果"""
    coin: str
    interval: str
    period: str
    
    # 基本统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # 收益指标
    total_return: float = 0
    final_balance: float = 0  # 最终余额
    max_balance: float = 0  # 最大余额
    min_balance: float = 0  # 最小余额
    win_rate: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    
    # 风险指标
    max_drawdown: float = 0
    max_profit: float = 0
    max_loss: float = 0
    
    # 风险调整收益
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    calmar_ratio: float = 0
    
    # 交易详情
    trades: List[Trade] = field(default_factory=list)
    
    # 信号统计
    buy_signals: int = 0
    sell_signals: int = 0
    
    # 日均开仓量
    daily_open_positions: float = 0  # 日均开仓数量


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        coin: str,
        interval: str = '1h',
        days: int = 1095,
        initial_capital: float = 500,
        enable_ttp: bool = True,
        stop_loss_pct: float = 0.1,
        leverage: float = 10.0,
        enable_withdraw: bool = True  # 启用自动提款功能
    ):
        self.coin = coin.upper()
        self.interval = interval
        self.days = days
        self.initial_capital = initial_capital
        self.enable_ttp = enable_ttp
        self.stop_loss_pct = stop_loss_pct
        self.leverage = leverage
        self.enable_withdraw = enable_withdraw  # 提款开关
        
        self.candles = self._load_data()
        
        if not self.candles:
            logger.error(f"无法获取 {coin} K线数据")
            self.candles = []
        
        self.trades: List[Trade] = []
        self.balance: List[float] = [initial_capital]
        self.current_balance: float = initial_capital  # 当前余额（实时更新）
        
        # 提款相关变量
        self.withdraw_count = 0  # 提款次数
        self.first_withdraw_day = None  # 第一次提款时的天数
        
        logger.info(f"🚀 回测初始化: {coin} {interval} ({days}天) | K线: {len(self.candles)} | 提款: {'开启' if enable_withdraw else '关闭'}")
    
    def _load_data(self):
        """加载K线数据"""
        data_file = os.path.join(DATA_DIR, 'historical', self.coin, f'{self.interval}.json')
        
        if not os.path.exists(data_file):
            logger.warning(f"数据文件不存在: {data_file}")
            return []
        
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            # 筛选指定天数的数据
            if self.days and len(data) > self.days * 24:
                data = data[-self.days * 24:]  # 1h = 24条/天
            
            logger.info(f"📁 加载数据: {len(data)} 条 | 文件: {data_file}")
            return data
            
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return []
    
    def _calculate_pip(self, price: float) -> float:
        """计算价格跳动点"""
        if price >= 1000:
            return 0.0001
        elif price >= 100:
            return 0.001
        elif price >= 10:
            return 0.0001
        else:
            return price * 0.0001
    
    def _check_withdraw(self, day_index: int = None) -> float:
        """检查是否需要提款
        
        Args:
            day_index: 当前是第几天
        
        Returns:
            提款金额（0表示不需要提款）
        """
        # 如果关闭了提款功能，直接返回0
        if not getattr(self, 'enable_withdraw', True):
            return 0
        
        WITHDRAW_THRESHOLD = 2000
        WITHDRAW_AMOUNT = 1000
        
        if self.balance[-1] > WITHDRAW_THRESHOLD:
            # 更新提款统计
            self.withdraw_count += 1
            if self.first_withdraw_day is None and day_index is not None:
                self.first_withdraw_day = day_index
            
            return WITHDRAW_AMOUNT
        return 0
    
    def run_backtest(self, strategy_name: str) -> BacktestResult:
        """运行回测"""
        if not self.candles:
            logger.error("没有K线数据，无法运行回测")
            return None
        
        # 创建策略
        strategy = get_strategy(strategy_name)
        if not strategy:
            logger.error(f"策略不存在: {strategy_name}")
            return None
        
        logger.info(f"📊 回测策略: {strategy_name}")
        
        closes = [c['close'] for c in self.candles]
        times = [datetime.fromtimestamp(c['time']/1000).strftime('%Y-%m-%d') for c in self.candles]
        
        position = None  # 当前持仓方向
        entry_price = 0  # 开仓价格
        
        # TTP 追踪变量
        high_since_entry = None  # 开仓后最高价
        low_since_entry = None   # 开仓后最低价
        swing_low = None          # 回调低点
        swing_high = None         # 回调高点
        ttp_level = None          # 移动止盈触发线
        previous_high = None      # 前高
        previous_low = None       # 前低
        
        # 信号计数
        buy_signals = 0
        sell_signals = 0
        
        n_candles = len(self.candles)
        start_idx = max(0, n_candles - self.days * 24)
        
        for i in range(start_idx, n_candles):
            try:
                # 兼容两种信号生成方式
                if hasattr(strategy, 'generate_signal'):
                    signal = strategy.generate_signal(self.coin, self.candles[:i+1])
                    if hasattr(signal, 'signal'):
                        action = signal.signal.value
                    else:
                        action = signal.value if isinstance(signal, Signal) else signal
                else:
                    signal = strategy.get_signal(i)
                    action = signal.value if isinstance(signal, Signal) else signal
            except Exception as e:
                logger.error(f"信号生成错误: {e}")
                action = 'HOLD'
            
            current_price = closes[i]
            current_time = times[i]
            
            # 计算 pip
            pip = self._calculate_pip(current_price)
            
            trade_capital = max(self.balance[-1] * 0.1, 100)
            position_size = trade_capital * self.leverage  # 开仓总额
            
            # ===== BUY 持仓的移动止盈检测 =====
            if self.enable_ttp and position == 'BUY' and self.balance[-1] > 0:
                floating_profit = (current_price - entry_price) / entry_price
                
                if floating_profit > 0:
                    # 创新高
                    if high_since_entry is None or current_price > high_since_entry:
                        previous_high = high_since_entry
                        high_since_entry = current_price
                    
                    # 回调更新 swing_low
                    if high_since_entry is not None and current_price < high_since_entry and current_price > entry_price:
                        if swing_low is None or current_price < swing_low:
                            swing_low = current_price
                    
                    # 涨过前高后设置 TTP
                    if previous_high is not None and current_price > previous_high:
                        if swing_low is not None and swing_low > entry_price:
                            new_ttp = swing_low - pip * 5
                            if ttp_level is None or new_ttp > ttp_level:
                                ttp_level = new_ttp
                    
                    # TTP 触发
                    if ttp_level is not None and current_price < ttp_level:
                        pnl = (ttp_level - entry_price) / entry_price * position_size
                        self.balance.append(self.balance[-1] + pnl)
                        new_balance = self.balance[-1]
                        
                        # 检查提款
                        day_index = (i - start_idx) // 24
                        withdraw = self._check_withdraw(day_index)
                        if withdraw > 0:
                            self.balance[-1] = self.balance[-1] - withdraw
                            new_balance = self.balance[-1]
                        
                        self.trades.append(Trade(current_time, 'TTP_BUY', current_price, trade_capital, pnl, new_balance, withdraw))
                        self.current_balance = new_balance
                        
                        position = None
                        previous_high = None
                        high_since_entry = None
                        swing_low = None
                        ttp_level = None
                        continue
            
            # ===== SELL 持仓的移动止盈检测 =====
            if self.enable_ttp and position == 'SELL' and self.balance[-1] > 0:
                floating_profit = (entry_price - current_price) / entry_price
                
                if floating_profit > 0:
                    # 创新低
                    if low_since_entry is None or current_price < low_since_entry:
                        previous_low = low_since_entry
                        low_since_entry = current_price
                    
                    # 回调更新 swing_high
                    if low_since_entry is not None and current_price > low_since_entry and current_price < entry_price:
                        if swing_high is None or current_price > swing_high:
                            swing_high = current_price
                    
                    # 跌破前低后设置 TTP
                    if previous_low is not None and current_price < previous_low:
                        if swing_high is not None and swing_high < entry_price:
                            new_ttp = swing_high + pip * 5
                            if ttp_level is None or new_ttp < ttp_level:
                                ttp_level = new_ttp
                    
                    # TTP 触发
                    if ttp_level is not None and current_price > ttp_level:
                        pnl = (entry_price - ttp_level) / entry_price * position_size
                        self.balance.append(self.balance[-1] + pnl)
                        new_balance = self.balance[-1]
                        
                        # 检查提款
                        day_index = (i - start_idx) // 24
                        withdraw = self._check_withdraw(day_index)
                        if withdraw > 0:
                            self.balance[-1] = self.balance[-1] - withdraw
                            new_balance = self.balance[-1]
                        
                        self.trades.append(Trade(current_time, 'TTP_SELL', current_price, trade_capital, pnl, new_balance, withdraw))
                        self.current_balance = new_balance
                        
                        position = None
                        previous_low = None
                        low_since_entry = None
                        swing_high = None
                        ttp_level = None
                        continue
            
            # 信号处理 - 按顺序检查
            # 1. BUY信号处理
            if action == 'BUY' and position != 'BUY':
                # 重置追踪变量
                previous_high = None
                high_since_entry = None
                swing_low = None
                ttp_level = None
                
                if position == 'SELL':
                    pnl = (entry_price - current_price) / entry_price * position_size
                    self.balance.append(self.balance[-1] + pnl)
                    new_balance = self.balance[-1]
                    
                    # 检查提款
                    day_index = (i - start_idx) // 24
                    withdraw = self._check_withdraw(day_index)
                    if withdraw > 0:
                        self.balance[-1] = self.balance[-1] - withdraw
                        new_balance = self.balance[-1]
                    
                    self.trades.append(Trade(current_time, 'CLOSE_SELL', current_price, trade_capital, pnl, new_balance, withdraw))
                    self.current_balance = new_balance
                    
                    if self.current_balance <= 0:
                        self.trades.append(Trade(current_time, 'LIQUIDATION', current_price, 0, 0, self.current_balance))
                        self.balance.append(0)
                        position = None
                        break
                    
                    self.trades.append(Trade(current_time, 'BUY', current_price, trade_capital, 0, self.current_balance))
                position = 'BUY'
                entry_price = current_price
                buy_signals += 1
            
            # 2. BUY持仓检测
            elif position == 'BUY':
                # BUY止损检测
                price_change = (current_price - entry_price) / entry_price
                if price_change <= -self.stop_loss_pct:
                    pnl = -position_size * self.stop_loss_pct
                    self.balance.append(self.balance[-1] + pnl)
                    new_balance = self.balance[-1]
                    
                    # 检查提款
                    day_index = (i - start_idx) // 24
                    withdraw = self._check_withdraw(day_index)
                    if withdraw > 0:
                        self.balance[-1] = self.balance[-1] - withdraw
                        new_balance = self.balance[-1]
                    
                    self.trades.append(Trade(current_time, 'CLOSE_BUY', current_price, trade_capital, pnl, new_balance, withdraw))
                    self.current_balance = new_balance
                    
                    if self.current_balance <= 0:
                        self.trades.append(Trade(current_time, 'LIQUIDATION', current_price, 0, 0, self.current_balance))
                        self.balance.append(0)
                        position = None
                        break
                    
                    position = None
                    previous_high = None
                    high_since_entry = None
                    swing_low = None
                    ttp_level = None
            
            # 3. SELL信号处理
            if action == 'SELL' and position != 'SELL':
                # 重置追踪变量
                previous_low = None
                low_since_entry = None
                swing_high = None
                ttp_level = None
                
                if position == 'BUY':
                    pnl = (current_price - entry_price) / entry_price * position_size
                    self.balance.append(self.balance[-1] + pnl)
                    new_balance = self.balance[-1]
                    
                    # 检查提款
                    day_index = (i - start_idx) // 24
                    withdraw = self._check_withdraw(day_index)
                    if withdraw > 0:
                        self.balance[-1] = self.balance[-1] - withdraw
                        new_balance = self.balance[-1]
                    
                    self.trades.append(Trade(current_time, 'CLOSE_BUY', current_price, trade_capital, pnl, new_balance, withdraw))
                    self.current_balance = new_balance
                    
                    if self.current_balance <= 0:
                        self.trades.append(Trade(current_time, 'LIQUIDATION', current_price, 0, 0, self.current_balance))
                        self.balance.append(0)
                        position = None
                        break
                
                self.trades.append(Trade(current_time, 'SELL', current_price, trade_capital, 0, self.current_balance))
                position = 'SELL'
                entry_price = current_price
                sell_signals += 1
            
            # 4. SELL持仓检测
            elif position == 'SELL':
                # SELL止损检测
                price_change = (entry_price - current_price) / entry_price
                if price_change <= -self.stop_loss_pct:
                    pnl = -position_size * self.stop_loss_pct
                    self.balance.append(self.balance[-1] + pnl)
                    new_balance = self.balance[-1]
                    
                    # 检查提款
                    day_index = (i - start_idx) // 24
                    withdraw = self._check_withdraw(day_index)
                    if withdraw > 0:
                        self.balance[-1] = self.balance[-1] - withdraw
                        new_balance = self.balance[-1]
                    
                    self.trades.append(Trade(current_time, 'CLOSE_SELL', current_price, trade_capital, pnl, new_balance, withdraw))
                    self.current_balance = new_balance
                    
                    if self.current_balance <= 0:
                        self.trades.append(Trade(current_time, 'LIQUIDATION', current_price, 0, 0, self.current_balance))
                        self.balance.append(0)
                        position = None
                        break
                    
                    position = None
                    previous_low = None
                    low_since_entry = None
                    swing_high = None
                    ttp_level = None
        
        # 结束时平仓
        final_price = self.candles[-1]['close']
        
        if position == 'BUY':
            pnl = (final_price - entry_price) / entry_price * position_size
            self.balance.append(self.balance[-1] + pnl)
            new_balance = self.balance[-1]
            
            # 检查提款

            if withdraw > 0:
                self.balance[-1] = self.balance[-1] - withdraw
                new_balance = self.balance[-1]
            
            self.trades.append(Trade(
                datetime.fromtimestamp(self.candles[-1]['time']/1000).strftime('%Y-%m-%d'),
                'CLOSE_BUY', final_price, trade_capital, pnl, new_balance, withdraw
            ))
            self.current_balance = new_balance
        
        elif position == 'SELL':
            pnl = (entry_price - final_price) / entry_price * position_size
            self.balance.append(self.balance[-1] + pnl)
            new_balance = self.balance[-1]
            
            # 检查提款

            if withdraw > 0:
                self.balance[-1] = self.balance[-1] - withdraw
                new_balance = self.balance[-1]
            
            self.trades.append(Trade(
                datetime.fromtimestamp(self.candles[-1]['time']/1000).strftime('%Y-%m-%d'),
                'CLOSE_SELL', final_price, trade_capital, pnl, new_balance, withdraw
            ))
            self.current_balance = new_balance
        
        return self._calculate_result(strategy_name, buy_signals, sell_signals)
    
    def _calculate_result(self, strategy_name: str, buy: int, sell: int) -> BacktestResult:
        """计算回测结果"""
        closing = [t for t in self.trades if t.order_type in ['CLOSE_BUY', 'CLOSE_SELL', 'TTP_BUY', 'TTP_SELL']]
        
        winning = [t for t in closing if t.pnl > 0]
        losing = [t for t in closing if t.pnl <= 0]
        
        # 最大回撤
        equity = [e for e in self.balance if e > 0]
        if not equity:
            equity = [0]
        max_eq = self.initial_capital
        max_dd = 0
        for e in equity:
            if e > max_eq:
                max_eq = e
            if max_eq > 0:
                dd = (max_eq - e) / max_eq * 100
                if dd > max_dd:
                    max_dd = dd
        
        # 计算收益
        final_balance = self.balance[-1]
        total_return = (final_balance - self.initial_capital) / self.initial_capital * 100
        
        # 风险调整收益
        returns = []
        for i in range(1, len(self.balance)):
            ret = (self.balance[i] - self.balance[i-1]) / self.balance[i-1]
            returns.append(ret)
        
        sharpe = 0
        sortino = 0
        
        if len(returns) > 1 and statistics.stdev(returns) > 0:
            risk_free_rate = 0.02 / 252  # 日无风险利率
            sharpe = (statistics.mean(returns) - risk_free_rate) / statistics.stdev(returns) * (252**0.5)
            
            negative_returns = [r for r in returns if r < 0]
            if len(negative_returns) > 1:
                sortino = (statistics.mean(returns) - risk_free_rate) / statistics.stdev(negative_returns) * (252**0.5)
        
        # 卡玛比率
        if max_dd > 0:
            calmar = total_return / max_dd
        else:
            calmar = 0
        
        # 胜率和盈亏比
        win_rate = len(winning) / len(closing) * 100 if closing else 0
        avg_win_pct = statistics.mean([t.pnl for t in winning]) / self.initial_capital * 100 if winning else 0
        avg_loss_pct = abs(statistics.mean([t.pnl for t in losing]) / self.initial_capital * 100) if losing else 0
        
        # TTP统计
        ttp_count = len([t for t in self.trades if 'TTP' in t.order_type])
        signal_close = len([t for t in self.trades if 'CLOSE' in t.order_type])
        
        # 日均开仓量
        open_trades = [t for t in self.trades if t.order_type in ['BUY', 'SELL']]
        trading_days = self.days if self.days > 0 else 1
        daily_open = len(open_trades) / trading_days if open_trades else 0
        
        return BacktestResult(
            coin=self.coin,
            interval=self.interval,
            period=f"{self.days}天",
            total_trades=len(closing),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_return=total_return,
            final_balance=final_balance,
            max_balance=max(self.balance) if self.balance else 0,
            min_balance=min(self.balance) if self.balance else 0,
            win_rate=win_rate,
            avg_win=avg_win_pct,
            avg_loss=avg_loss_pct,
            max_drawdown=max_dd,
            max_profit=max([t.pnl for t in closing]) if closing else 0,
            max_loss=min([t.pnl for t in closing]) if closing else 0,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            trades=self.trades,
            buy_signals=buy,
            sell_signals=sell,
            daily_open_positions=daily_open
        )
    
    def save_report(self, strategy_name: str, prefix: str = "TTP"):
        """保存回测报告"""
        if not self.candles:
            return
        
        # 计算avg_win/avg_loss金额
        avg_win = statistics.mean([t.pnl for t in self.trades if t.pnl > 0 and 'CLOSE' in t.order_type]) if [t for t in self.trades if t.pnl > 0 and 'CLOSE' in t.order_type] else 0
        avg_loss = abs(statistics.mean([t.pnl for t in self.trades if t.pnl < 0 and 'CLOSE' in t.order_type])) if [t for t in self.trades if t.pnl < 0 and 'CLOSE' in t.order_type] else 0
        
        # 转换时长为中文
        days_map = {
            365: "1年",
            730: "2年",
            1095: "3年",
            1825: "5年",
        }
        duration = days_map.get(self.days, f"{self.days}天")
        
        # 系统名称
        system_name = "backtest"
        
        # 安全值转换
        def safe_value(v):
            if v is None:
                return 0
            if isinstance(v, float):
                return round(v, 2)
            return v
        
        # 百分比格式化
        def format_pct(v):
            if v is None:
                return "0.00%"
            return f"{v:.2f}%"
        
        result = self._calculate_result(strategy_name, 0, 0)
        
        # 计算盈利因子和期望比率
        winning = [t for t in self.trades if t.pnl > 0 and 'CLOSE' in t.order_type]
        losing = [t for t in self.trades if t.pnl < 0 and 'CLOSE' in t.order_type]
        gross_profit = sum(t.pnl for t in winning)
        gross_loss = sum(t.pnl for t in losing)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        expectancy = (result.win_rate/100 * avg_win/100) - ((1 - result.win_rate/100) * avg_loss/100) if result.win_rate > 0 else 0
        
        # 连胜连亏
        closing = [t for t in self.trades if 'CLOSE' in t.order_type]
        longest_win = 0
        longest_loss = 0
        current_win = 0
        current_loss = 0
        for t in closing:
            if t.pnl > 0:
                current_win += 1
                current_loss = 0
                longest_win = max(longest_win, current_win)
            else:
                current_loss += 1
                current_win = 0
                longest_loss = max(longest_loss, current_loss)
        
        # TTP统计
        ttp_count = len([t for t in self.trades if 'TTP' in t.order_type])
        signal_close = len([t for t in self.trades if 'CLOSE' in t.order_type])
        
        report_data = {
            'strategy': strategy_name,
            'config': {
                'coin': self.coin,
                'interval': self.interval,
                'period': duration,
                'initial_capital': self.initial_capital,
                'leverage': self.leverage,
                'stop_loss': f"{self.stop_loss_pct*100:.0f}%",
                'enable_ttp': self.enable_ttp,
                'trade_percent': 0.1,  # 每次开仓使用余额的10%
            },
            'balance': {
                'initial': self.initial_capital,
                'final': safe_value(result.final_balance),
                'max': safe_value(result.max_balance),
                'min': safe_value(result.min_balance),
                'withdraw_count': self.withdraw_count,  # 提款次数
                'first_time_withdraw': f"第{self.first_withdraw_day}天" if self.first_withdraw_day is not None else "无",  # 第一次提款时的天数
            },
            'results': {
                'total_return': format_pct(safe_value(result.total_return)),  # 总收益%
                'max_drawdown': format_pct(safe_value(result.max_drawdown)),  # 最大回撤%
                'sharpe_ratio': safe_value(result.sharpe_ratio),  # 夏普比率
                'sortino_ratio': safe_value(result.sortino_ratio),  # 索提诺比率
                'calmar_ratio': safe_value(result.calmar_ratio),  # 卡玛比率
                'total_trades': safe_value(result.total_trades),  # 总交易数
                'winning_trades': safe_value(result.winning_trades),  # 盈利交易
                'losing_trades': safe_value(result.losing_trades),  # 亏损交易
                'win_rate': format_pct(safe_value(result.win_rate)),  # 胜率%
                'avg_win': format_pct(safe_value(result.avg_win)),  # 平均盈利%
                'avg_loss': format_pct(safe_value(result.avg_loss)),  # 平均亏损%
                'max_win': f"${safe_value(result.max_profit)}",  # 最大单笔盈利金额
                'max_loss': f"${safe_value(result.max_loss)}",  # 最大单笔亏损金额
                'profit_factor': safe_value(profit_factor),  # 盈利因子
                'expectancy_ratio': round(expectancy, 2),  # 期望比率
                'longest_win': safe_value(longest_win),  # 最长连胜
                'longest_loss': safe_value(longest_loss),  # 最长连亏
                'ttp_count': ttp_count,  # TTP止盈次数
                'signal_close': signal_close,  # 信号平仓次数
                'daily_open_positions': round(result.daily_open_positions, 2),  # 日均开仓量
            },
            'trades': [
                {
                    'time': t.time,
                    'order_type': t.order_type,
                    'price': t.price,
                    'capital': t.capital,
                    'pnl': t.pnl,
                    'balance': t.balance,
                    'withdraw': t.withdraw  # 从Trade对象获取
                }
                for t in self.trades
            ]
        }
        
        # 保存文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 提款状态标识
        withdraw_status = "有提款" if getattr(self, 'enable_withdraw', True) else "无提款"
        
        prefix_str = f"{prefix}_" if prefix else ""
        report_file = os.path.join(
            REPORT_DIR, 
            f'{prefix_str}{self.coin}_{strategy_name}_{self.interval}_{duration}_{withdraw_status}_{system_name}_{timestamp}.json'
        )
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📁 报告已保存: {report_file}")
        
        # 打印摘要
        print("=" * 60)
        print(f"💰 最终余额: ${result.final_balance:,.2f}")
        print(f"💰 最大余额: ${result.max_balance:,.2f}")
        print(f"💰 最小余额: ${result.min_balance:,.2f}")
        print("=" * 60)
        print(f"📈 总收益率: {format_pct(result.total_return)}")
        print(f"📉 最大回撤: {format_pct(result.max_drawdown)}")
        print(f"📊 日均开仓: {result.daily_open_positions:.2f}笔")
        print(f"📊 夏普比率: {result.sharpe_ratio:.2f}")
        print(f"📊 索提诺: {result.sortino_ratio:.2f}")
        print(f"📊 卡玛比率: {result.calmar_ratio:.2f}")
        print(f"🎯 胜率: {result.win_rate:.1f}%")
        print(f"💰 总交易次数: {result.total_trades}")
        print(f"📊 日均开仓: {result.daily_open_positions:.2f}笔")
        print(f"🎯 TTP止盈: {ttp_count} ({ttp_count/result.total_trades*100:.1f}%)" if result.total_trades > 0 else "🎯 TTP止盈: 0")
        print(f"🎯 信号平仓: {signal_close} ({signal_close/result.total_trades*100:.1f}%)" if result.total_trades > 0 else "🎯 信号平仓: 0")
        print("=" * 60)
        
        return result


def run_backtest(coin: str, strategy_name: str, interval: str = '1h', days: int = 1095, initial_capital: float = 500):
    """便捷回测函数"""
    engine = BacktestEngine(
        coin=coin,
        interval=interval,
        days=days,
        initial_capital=initial_capital,
        enable_ttp=True,
        stop_loss_pct=0.1,
        leverage=10.0
    )
    result = engine.run_backtest(strategy_name)
    engine.save_report(strategy_name)
    return result
