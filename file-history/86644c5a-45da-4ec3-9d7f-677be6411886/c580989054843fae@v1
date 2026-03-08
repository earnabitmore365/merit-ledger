# Abby Auto-Trading 重构完整文档

**项目**: Abby Auto-Trading 自主交易系统
**版本**: 1.0
**状态**: 重构中
**时间**: 2026-02-20

---

## 📋 目录

1. [整体架构](#1-整体架构)
2. [统一词汇表](#2-统一词汇表)
3. [目录结构](#3-目录结构)
4. [核心接口设计](#4-核心接口设计)
5. [模块详细设计](#5-模块详细设计)
6. [代码规范](#6-代码规范)
7. [资源调用指南](#7-资源调用指南)
8. [验证清单](#8-验证清单)

---

## 1. 整体架构

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Abby Auto-Trading 架构                            │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   Config        │  配置文件
                              │   (配置管理)    │
                              └────────┬────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          TradingSystem                                   │
│                         (交易系统主控)                                    │
│                                                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │   Executor      │  │   Arbitrage    │  │  RiskManager   │        │
│  │   (执行器)       │  │   (套利仲裁)    │  │  (风险管理)     │        │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │
│           │                     │                     │                   │
│           └─────────────────────┼─────────────────────┘                   │
│                                 │                                         │
│                                 ▼                                         │
│                    ┌──────────────────────┐                              │
│                    │   Exchange Adapters │                              │
│                    │   (交易所适配器层)   │                              │
│                    └──────────┬─────────┘                              │
│                               │ │                                        │
│              ┌──────────────┘ └──────────────┐                         │
│              ▼                                   ▼                         │
│    ┌─────────────────┐             ┌─────────────────┐                 │
│    │  HyperLiquid    │             │    Binance      │                 │
│    │  Adapter        │             │    Adapter      │                 │
│    └────────┬────────┘             └────────┬────────┘                 │
│             │                               │                           │
│             ▼                               ▼                           │
│    ┌─────────────────┐             ┌─────────────────┐                 │
│    │  HyperLiquid    │             │    Binance      │                 │
│    │  API            │             │    API          │                 │
│    └─────────────────┘             └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   Strategies    │  策略层
                              │   (策略生成信号) │
                              └─────────────────┘
```

### 1.2 数据流

```
K线数据 → 策略 → 信号 → 风险管理 → 执行器 → 交易所
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
Exchange   Strategy   RiskMgr   Executor   Exchange
Adapter    (生成)     (检查)    (执行)    Adapter
```

### 1.3 核心原则

| 原则 | 说明 |
|------|------|
| **所有功能都是调用的** | 不直接调用 API，通过适配器 |
| **单一职责** | 每个模块只做一件事 |
| **依赖倒置** | 高层模块不依赖低层模块，都依赖抽象 |
| **开闭原则** | 对扩展开放，对修改封闭 |

---

## 2. 统一词汇表

### 2.1 核心词汇

| 英文 | 中文 | 说明 | 示例 |
|------|------|------|------|
| Exchange | 交易所 | 交易平台 | HyperLiquid, Binance |
| Adapter | 适配器 | 交易所与系统的桥梁 | `HyperLiquidAdapter` |
| Strategy | 策略 | 生成交易信号 | VWAP, BB Squeeze |
| Signal | 信号 | 交易决策 | BUY, SELL, HOLD |
| Position | 持仓 | 当前仓位状态 | `{"coin": "ETH", "size": 1.5}` |
| Order | 订单 | 交易请求 | `Order(coin="ETH", side="BUY")` |
| Stop Loss | 止损 | 亏损时平仓 | 亏损 > 10% 时止损 |
| TTP | 移动止盈 | 盈利时跟踪止盈 | 回调低点 - 5 pips |
| Arbitrage | 套利 | 跨交易所价差交易 | 低买高卖 |
| Executor | 执行器 | 执行交易订单 | 调用交易所 API |

### 2.2 文件命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 适配器 | `exchange_{name}.py` | `hyperliquid.py`, `binance.py` |
| 策略 | `strategy_{name}.py` | `strategy_vwap.py`, `strategy_bb.py` |
| 风险管理 | `{risk_type}.py` | `stop_loss.py`, `ttp.py` |
| 工具 | `{用途}.py` | `logger.py`, `config.py` |

### 2.3 类名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 适配器 | `{Exchange}Adapter` | `HyperLiquidAdapter` |
| 策略 | `{StrategyName}Strategy` | `VWAPStrategy` |
| 风险管理 | `{RiskType}Manager` | `StopLossManager` |
| 异常 | `{Module}{Error}` | `ExchangeError`, `OrderError` |

---

## 3. 目录结构

### 3.1 完整目录

```
abby-auto-trading/
│
├── logs/                      # 日志目录
│   ├── trading/             # 交易日志
│   ├── backtest/           # 回测日志
│   └── live/              # 自动交易日志
│
├── reports/                 # 报告目录
│   ├── trading/           # 交易报告
│   ├── backtest/         # 回测报告
│   └── live/            # 自动交易报告
│
├── src/                     # 源代码
│   │
│   ├── core/              # 核心模块
│   │   ├── strategy/     # 策略（生成信号）
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # 策略基类
│   │   │   ├── strategy_vwap.py
│   │   │   └── strategy_bb_squeeze.py
│   │   │   └── ...          # 40+ 策略
│   │   │
│   │   └── risk/        # 风险管理
│   │       ├── base.py       # 风险管理基类
│   │       ├── stop_loss.py  # 止损实现
│   │       └── ttp.py       # 移动止盈实现
│   │
│   ├── exchange/        # 交易所适配器
│   │   ├── base.py          # 适配器基类
│   │   ├── __init__.py
│   │   │
│   │   ├── hyperliquid/     # HyperLiquid
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py    # HL 适配器
│   │   │   └── websocket.py     # HL 客户端
│   │   │
│   │   └── binance/         # Binance（未来）
│   │       ├── __init__.py
│   │       └── adapter.py
│   │
│   ├── trading/         # 交易系统
│   │   ├── __init__.py
│   │   ├── system.py        # 交易系统主控
│   │   ├── executor.py       # 执行器
│   │   └── arbitrage.py      # 套利仲裁
│   │
│   ├── interface/       # 乖女儿用的内部接口
│   │   ├── __init__.py
│   │   ├── main.py           # CLI 界面
│   │   └── run_run_bot.py           # Telegram Bot
│   │
│   ├── backtest/       # 回测系统
│   │   ├── __init__.py
│   │   ├── engine.py        # 回测引擎
│   │   └── analyzer.py      # 结果分析
│   │
│   ├── utils/          # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py        # 日志工具
│   │   ├── config.py        # 配置工具
│   │   └── metrics.py       # 指标计算
│   │
│   └── config/         # 配置文件
│       ├── __init__.py
│       ├── default.json      # 默认配置
│       └── secrets.json      # 密钥配置（不提交）
│
├── user_interface/     # 用户界面（根目录）
│   └── backtest_system.command  # 回测快捷脚本
│
├── README.md
└── requirements.txt
```

### 3.2 模块职责

| 模块 | 职责 |
|------|------|
| `core/strategy/` | 策略实现，生成交易信号 |
| `core/risk/` | 风险管理，止损/止盈 |
| `exchange/` | 交易所适配器，API 调用 |
| `trading/` | 交易主控，执行器，套利 |
| `interface/` | 乖女儿用的内部接口 |
| `backtest/` | 回测系统 |
| `utils/` | 通用工具 |
| `config/` | 配置文件 |
| `user_interface/` | 用户界面（根目录） |

---

## 4. 核心接口设计

### 4.1 交易所适配器基类

```python
#!/usr/bin/env python3
"""
Exchange Adapter Base

交易所适配器基类
所有交易所适配器都必须实现以下接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class OrderSide(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class OrderRequest:
    """订单请求"""
    coin: str
    side: OrderSide
    order_type: OrderType
    size: float
    price: Optional[float] = None


@dataclass
class OrderResult:
    """订单结果"""
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    filled_price: Optional[float] = None
    filled_size: Optional[float] = None


@dataclass
class Position:
    """持仓信息"""
    coin: str
    side: str  # "LONG" or "SHORT"
    size: float
    entry_price: float
    unrealized_pnl: float


class ExchangeAdapter(ABC):
    """交易所适配器基类
    
    所有交易所适配器都必须继承此类并实现所有抽象方法
    
    Usage:
        class HyperLiquidAdapter(ExchangeAdapter):
            def get_price(self, coin: str) -> float:
                ...
    """
    
    def __init__(self, config: Dict):
        """初始化
        
        Args:
            config: 交易所配置（API Key, Secret 等）
        """
        self.config = config
        self._connected = False
    
    # ==================== 连接管理 ====================
    
    @abstractmethod
    def connect(self) -> bool:
        """连接交易所"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass
    
    # ==================== 行情数据 ====================
    
    @abstractmethod
    def get_price(self, coin: str) -> float:
        """获取当前价格
        
        Args:
            coin: 币种名称（如 "ETH"）
        
        Returns:
            float: 当前价格
        """
        pass
    
    @abstractmethod
    def get_klines(self, coin: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """获取 K 线数据
        
        Args:
            coin: 币种名称
            interval: K 线周期（1m, 5m, 15m, 1h, 4h）
            limit: 获取数量
        
        Returns:
            List[Dict]: K 线数据列表
            [{
                'timestamp': 1234567890,
                'open': 100.0,
                'high': 105.0,
                'low': 99.0,
                'close': 103.0,
                'volume': 1000.0,
            }]
        """
        pass
    
    # ==================== 订单操作 ====================
    
    @abstractmethod
    def place_order(self, order: OrderRequest) -> OrderResult:
        """下单
        
        Args:
            order: 订单请求
        
        Returns:
            OrderResult: 订单结果
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """取消订单
        
        Args:
            order_id: 订单 ID
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict:
        """查询订单状态
        
        Args:
            order_id: 订单 ID
        
        Returns:
            Dict: 订单状态
        """
        pass
    
    # ==================== 持仓管理 ====================
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """获取所有持仓
        
        Returns:
            List[Position]: 持仓列表
        """
        pass
    
    @abstractmethod
    def get_position(self, coin: str) -> Optional[Position]:
        """获取指定币种持仓
        
        Args:
            coin: 币种名称
        
        Returns:
            Optional[Position]: 持仓信息，不存在返回 None
        """
        pass
    
    # ==================== 账户管理 ====================
    
    @abstractmethod
    def get_balance(self) -> Dict:
        """获取账户余额
        
        Returns:
            Dict: 余额信息
            {
                'usdc': 1000.0,
                'available': 900.0,
            }
        """
        pass
    
    # ==================== 工具方法 ====================
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def get_exchange_name(self) -> str:
        """获取交易所名称（子类实现）"""
        raise NotImplementedError
```

### 4.2 策略基类

```python
#!/usr/bin/env python3
"""
Strategy Base

策略基类
所有策略都必须继承此类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class Signal(Enum):
    """交易信号"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """带信息的交易信号"""
    signal: Signal
    confidence: float = 1.0  # 置信度 0-1
    info: str = ""  # 信号说明
    metadata: Dict = None  # 附加信息


class Strategy(ABC):
    """策略基类
    
    所有策略都必须继承此类并实现 generate_signal 方法
    
    Usage:
        class VWAPStrategy(Strategy):
            def generate_signal(self, coin: str, klines: List[Dict]) -> Signal:
                ...
    """
    
    def __init__(self, name: str = "base"):
        """初始化
        
        Args:
            name: 策略名称
        """
        self.name = name
    
    @abstractmethod
    def generate_signal(self, coin: str, klines: List[Dict]) -> Signal:
        """生成交易信号
        
        Args:
            coin: 币种名称
            klines: K 线数据
        
        Returns:
            Signal: BUY / SELL / HOLD
        """
        pass
    
    def get_params(self) -> Dict:
        """获取策略参数
        
        Returns:
            Dict: 策略参数
        """
        return {}
    
    def set_params(self, **params):
        """设置策略参数
        
        Args:
            **params: 参数键值对
        """
        pass
    
    def validate_klines(self, klines: List[Dict]) -> bool:
        """验证 K 线数据
        
        Args:
            klines: K 线数据
        
        Returns:
            bool: 数据是否有效
        """
        if not klines or len(klines) < 10:
            return False
        return True
```

### 4.3 风险管理基类

```python
#!/usr/bin/env python3
"""
Risk Manager Base

风险管理基类
所有风险管理模块都必须实现以下接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RiskConfig:
    """风险管理配置"""
    stop_loss_pct: float = 0.10  # 止损比例 10%
    ttp_enabled: bool = True      # 是否启用移动止盈
    ttp_buffer_pips: float = 5.0  # TTP 缓冲 pips
    max_position_pct: float = 0.5  # 最大仓位比例 50%


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    should_close: bool = False  # 是否应该平仓
    reason: str = ""           # 原因
    confidence: float = 1.0    # 置信度


class RiskManager(ABC):
    """风险管理基类
    
    所有风险管理模块都必须继承此类
    
    Usage:
        class StopLossManager(RiskManager):
            def check(self, position: Dict, current_price: float) -> RiskCheckResult:
                ...
    """
    
    def __init__(self, config: RiskConfig = None):
        """初始化
        
        Args:
            config: 风险管理配置
        """
        self.config = config or RiskConfig()
    
    @abstractmethod
    def check(self, position: Dict, current_price: float, **kwargs) -> RiskCheckResult:
        """风险检查
        
        Args:
            position: 持仓信息
            current_price: 当前价格
            **kwargs: 附加参数
        
        Returns:
            RiskCheckResult: 检查结果
        """
        pass
    
    def reset(self) -> None:
        """重置状态"""
        pass
```

---

## 5. 模块详细设计

### 5.1 交易系统主控 (trading/system.py)

```python
#!/usr/bin/env python3
"""
Trading System

交易系统主控
整合策略、风险管理、交易所适配器
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.core.strategy.base import Strategy, Signal
from src.core.risk.base import RiskManager, RiskCheckResult
from src.exchange.base import ExchangeAdapter, OrderRequest, OrderSide, OrderType


class TradingSystem:
    """交易系统主控
    
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
        self.logger = logging.getLogger(__name__)
    
    def run(self, interval_seconds: int = 60):
        """运行交易系统
        
        Args:
            interval_seconds: 执行间隔（秒）
        """
        self.running = True
        self.logger.info("交易系统启动")
        
        try:
            while self.running:
                self.run_once()
                self._sleep(interval_seconds)
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
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
        }
        
        try:
            # 1. 获取 K 线数据
            klines = self._get_klines()
            if not klines:
                return result
            
            # 2. 生成信号
            signal = self._generate_signal(klines)
            result['signal'] = signal.value
            
            # 3. 同步持仓
            self._sync_position()
            
            # 4. 风险管理检查
            if self.position and self.risk_manager:
                risk_result = self._check_risk()
                if risk_result.should_close:
                    self._close_position(risk_result.reason)
                    result['action'] = risk_result.reason
                    return result
            
            # 5. 执行交易
            if signal == Signal.BUY and not self.position:
                self._open_position("BUY")
                result['action'] = "OPEN_LONG"
            elif signal == Signal.SELL and not self.position:
                self._open_position("SELL")
                result['action'] = "OPEN_SHORT"
            
        except Exception as e:
            self.logger.error(f"执行错误: {e}")
        
        return result
    
    def stop(self):
        """停止交易系统"""
        self.running = False
        self.logger.info("交易系统已停止")
    
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
        positions = self.exchange.get_positions()
        if positions:
            pos = positions[0]
            self.position = pos['side']
            self.entry_price = pos.get('entry_price', 0.0)
        else:
            self.position = None
    
    def _check_risk(self) -> RiskCheckResult:
        """风险管理检查"""
        if not self.position:
            return RiskCheckResult(should_close=False)
        
        coin = self.config.get('coin', 'ETH')
        position = self.exchange.get_position(coin)
        current_price = self.exchange.get_price(coin)
        
        return self.risk_manager.check(position, current_price)
    
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
            self.logger.info(f"开仓: {side} {coin} @ {current_price}")
    
    def _close_position(self, reason: str = "CLOSE"):
        """平仓"""
        if not self.position:
            return
        
        coin = self.config.get('coin', 'ETH')
        result = self.exchange.close_position(coin)
        
        if result.success:
            self.position = None
            self.logger.info(f"平仓: {reason} {coin}")
    
    def _sleep(self, seconds: int):
        """休眠"""
        import time
        time.sleep(seconds)
```

---

## 6. 代码规范

### 6.1 文件结构

```python
#!/usr/bin/env python3
"""
模块名称

功能描述：
- 功能1
- 功能2

依赖：
- module1
- module2

Usage:
    用法示例
"""

# ==================== 导入部分 ====================
import os
from typing import Dict, List

# ==================== 配置 ====================
DEFAULT_COIN = "ETH"

# ==================== 类定义 ====================
class MyClass:
    """类的功能描述"""
    
    def __init__(self):
        """初始化"""
        pass

# ==================== 核心函数 ====================
def core_function(param: str) -> bool:
    """函数说明
    
    Args:
        param: 参数说明
    
    Returns:
        bool: 返回值说明
    """
    pass

# ==================== 辅助函数 ====================
def helper_function():
    """辅助函数说明"""
    pass

# ==================== 主程序 ====================
if __name__ == "__main__":
    main()
```

### 6.2 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块名 | snake_case | `trading_system.py` |
| 类名 | PascalCase | `TradingSystem` |
| 函数名 | snake_case | `get_price()` |
| 变量名 | snake_case | `current_price` |
| 常量名 | UPPER_SNAKE_CASE | `MAX_POSITION` |
| 私有方法 | `_private_method()` | `_sync_position()` |

---

## 7. 资源调用指南

### 7.1 可用的工具

| 工具 | 用途 | 示例 |
|------|------|------|
| read | 读取文件 | `read("src/exchange/base.py")` |
| write | 写入文件 | `write("new_file.py", content)` |
| edit | 编辑文件 | `edit(path, oldText, newText)` |
| exec | 执行命令 | `exec("python main.py")` |
| web_search | 搜索 | `web_search("HyperLiquid API")` |
| web_fetch | 获取网页 | `web_fetch(url)` |

### 7.2 代码复用

**复用已有代码：**

```python
# 复用已有适配器
from src.exchange.hyperliquid.adapter import HyperLiquidAdapter

# 复用策略
from src.core.strategy import get_strategy

# 复用配置
from src.config import config_manager
```

---

## 8. 验证清单

### 8.1 交易所适配器

- [ ] `exchange/base.py` 语法正确
- [ ] `exchange/hyperliquid/adapter.py` 导入正常
- [ ] 支持 `get_price()`
- [ ] 支持 `get_klines()`
- [ ] 支持 `place_order()`
- [ ] 支持 `get_positions()`
- [ ] 支持 `get_balance()`

### 8.2 风险管理

- [ ] `core/risk/base.py` 语法正确
- [ ] `core/risk/stop_loss.py` 导入正常
- [ ] `core/risk/ttp.py` 导入正常
- [ ] 支持固定止损
- [ ] 支持跟踪止损

### 8.3 交易系统

- [ ] `trading/system.py` 导入正常
- [ ] `trading/executor.py` 导入正常
- [ ] `trading/arbitrage.py` 导入正常
- [ ] 所有模块可以互相调用
- [ ] 支持多个交易所

### 8.4 通用检查

- [ ] 所有文件符合代码规范
- [ ] 所有类都有文档字符串
- [ ] 所有函数都有类型注解
- [ ] 没有硬编码的配置

---

**乖女儿会按照这个文档完整重构交易系统！** 💕
