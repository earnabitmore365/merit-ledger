#!/usr/bin/env python3
"""
Configuration Management

配置管理 - 集中管理所有配置项
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json
import os


@dataclass
class TradingConfig:
    """交易配置"""
    leverage: float = 10.0
    position_size_pct: float = 0.1  # 10% 仓位
    max_positions: int = 3
    stop_loss_pct: float = 0.1  # 10% 止损
    take_profit_pct: float = 0.2  # 20% 止盈


@dataclass
class TTPConfig:
    """移动止盈配置"""
    enabled: bool = True
    trailing_pips: float = 5.0
    min_profit_pips: float = 10.0
    swing_lookback: int = 5


@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str = "hyperliquid"
    api_key: str = ""
    api_secret: str = ""
    account_address: str = ""
    testnet: bool = True


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 10000.0
    fee_pct: float = 0.001  # 0.1% 手续费
    slippage_pct: float = 0.001  # 0.1% 滑点
    use_local_data: bool = True


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str = ""
    params: Dict = field(default_factory=dict)


@dataclass
class AppConfig:
    """应用配置"""
    name: str = "Abby Auto Trading"
    version: str = "1.0.0"
    mode: str = "backtest"  # backtest, paper, live
    
    # 子配置
    trading: TradingConfig = field(default_factory=TradingConfig)
    ttp: TTPConfig = field(default_factory=TTPConfig)
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/abby_trading.log"


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: str = "config/config.json"):
        self.config_file = Path(config_file)
        self.config = AppConfig()
        self.load()

    def load(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # 更新配置
                if 'trading' in data:
                    self.config.trading = TradingConfig(**data['trading'])
                if 'ttp' in data:
                    self.config.ttp = TTPConfig(**data['ttp'])
                if 'exchange' in data:
                    self.config.exchange = ExchangeConfig(**data['exchange'])
                if 'backtest' in data:
                    self.config.backtest = BacktestConfig(**data['backtest'])
                
                print(f"✅ 加载配置: {self.config_file}")
            except Exception as e:
                print(f"⚠️ 加载配置失败: {e}")
                print("使用默认配置")
        else:
            print(f"⚠️ 配置文件不存在: {self.config_file}")
            print("使用默认配置")
            self.save()

    def save(self):
        """保存配置"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'name': self.config.name,
            'version': self.config.version,
            'mode': self.config.mode,
            'trading': {
                'leverage': self.config.trading.leverage,
                'position_size_pct': self.config.trading.position_size_pct,
                'max_positions': self.config.trading.max_positions,
                'stop_loss_pct': self.config.trading.stop_loss_pct,
                'take_profit_pct': self.config.trading.take_profit_pct
            },
            'ttp': {
                'enabled': self.config.ttp.enabled,
                'trailing_pips': self.config.ttp.trailing_pips,
                'min_profit_pips': self.config.ttp.min_profit_pips,
                'swing_lookback': self.config.ttp.swing_lookback
            },
            'exchange': {
                'name': self.config.exchange.name,
                'testnet': self.config.exchange.testnet
            },
            'backtest': {
                'initial_capital': self.config.backtest.initial_capital,
                'fee_pct': self.config.backtest.fee_pct,
                'slippage_pct': self.config.backtest.slippage_pct,
                'use_local_data': self.config.backtest.use_local_data
            },
            'log_level': self.config.log_level
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ 保存配置: {self.config_file}")

    def get(self, key: str):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return None
        
        return value

    def set(self, key: str, value):
        """设置配置值"""
        keys = key.split('.')
        obj = self.config
        
        for k in keys[:-1]:
            if hasattr(obj, k):
                obj = getattr(obj, k)
        
        if hasattr(obj, keys[-1]):
            setattr(obj, keys[-1], value)
            self.save()


# 默认配置
DEFAULT_CONFIG = {
    "name": "Abby Auto Trading",
    "version": "1.0.0",
    "mode": "backtest",
    "trading": {
        "leverage": 10.0,
        "position_size_pct": 0.1,
        "max_positions": 3,
        "stop_loss_pct": 0.1,
        "take_profit_pct": 0.2
    },
    "ttp": {
        "enabled": True,
        "trailing_pips": 5.0,
        "min_profit_pips": 10.0,
        "swing_lookback": 5
    },
    "exchange": {
        "name": "hyperliquid",
        "testnet": True
    },
    "backtest": {
        "initial_capital": 10000.0,
        "fee_pct": 0.001,
        "slippage_pct": 0.001,
        "use_local_data": True
    },
    "log_level": "INFO"
}


if __name__ == "__main__":
    # 创建默认配置
    config = ConfigManager("config/default_config.json")
    config.save()
    print(config.config)
