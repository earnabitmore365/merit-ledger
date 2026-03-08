#!/usr/bin/env python3
"""
Strategy Package

策略包
自动扫描并导入所有策略
"""

from .base import Strategy, Signal, TradingSignal, register_strategy, get_strategy, list_strategies

__all__ = ['Strategy', 'Signal', 'TradingSignal', 'register_strategy', 'get_strategy', 'list_strategies']

import pkgutil
from pathlib import Path
import sys

_CURRENT_DIR = Path(__file__).parent

# 自动扫描所有模块
_modules = []
for module_info in pkgutil.iter_modules([str(_CURRENT_DIR)]):
    module_name = module_info.name
    if not module_name.startswith('_') and not module_name == 'base':
        _modules.append(module_name)

__all__ += _modules

# 延迟导入所有模块
for module_name in _modules:
    try:
        exec(f"from .{module_name} import *")
    except Exception as e:
        pass

# 自动注册所有 Strategy 子类
from .base import _STRATEGY_REGISTRY

for module_name in _modules:
    try:
        full_module_name = f'core.strategy.{module_name}'
        if full_module_name not in sys.modules:
            __import__(full_module_name)

        mod = sys.modules.get(full_module_name)
        if mod:
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, Strategy) and attr is not Strategy:
                    # 自动从类名生成策略名
                    # 特殊处理：MA -> ma, RSI -> rsi 等
                    strategy_name = attr_name
                    # 去掉常见后缀
                    for suffix in ['Strategy', '_']:
                        if strategy_name.endswith(suffix):
                            strategy_name = strategy_name[:-len(suffix)]
                    # 转换为小写
                    strategy_name = strategy_name.lower()
                    if strategy_name not in _STRATEGY_REGISTRY:
                        register_strategy(strategy_name, attr)
    except Exception as e:
        pass  # 忽略错误
