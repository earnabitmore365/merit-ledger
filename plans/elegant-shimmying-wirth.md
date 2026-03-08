# TTP Testnet 测试计划

## Context
用户希望在 HyperLiquid 测试网上测试 TTP（移动止盈）功能。TTP 逻辑已集成到 `run_bot.py` 中，使用统一的 `TTPManager` 类。

## 当前状态
- TTP 逻辑已实现于 `src/core/risk/ttp.py`
- 已集成到 `src/interface/run_bot.py` 和 `src/backtest/backtest.py`
- 回测显示 TTP 在 30 天内触发了 13 次

## 实施步骤

### 1. 运行测试网机器人
```bash
cd /Users/allenbot/.claude/projects/abby-auto-trading
python -m src.interface.run_bot --coin ETH --interval 1h --mode paper
```

### 2. 监控执行
- 机器人每 60 秒执行一次 step()
- 检查日志输出：
  - 获取 K 线数据
  - 止损检查
  - TTP 检查
  - 信号生成
  - 订单执行

### 3. 验证 TTP 逻辑
当有持仓时，TTP 逻辑流程：
1. 浮盈 >= 1% 启动追踪
2. 创新高后确认继续涨（再次创新高）
3. 回调时设置 TTP（基于回调低点 - pips）
4. 价格跌破 TTP 时触发平仓

## 测试文件
- `src/interface/run_bot.py` - 主机器人入口
- `src/core/risk/ttp.py` - TTP 逻辑
- `src/exchange/hyperliquid/adapter.py` - 交易所适配器

## 验证方法
1. 运行机器人，等待开仓信号
2. 观察 TTP 相关日志输出
3. 确认 TTP 在浮盈达到 1% 后开始追踪
4. 确认创新高、确认、回调后设置 TTP level
5. 价格触发 TTP 时自动平仓
