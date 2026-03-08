#!/usr/bin/env python3
"""
Abby Auto Trading - CLI Interface

Main entry point for the trading system.
"""

import sys
import argparse
from pathlib import Path

# Add src to path - 需要添加父目录
_project_root = Path(__file__).parent.parent
_src_dir = _project_root / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from datetime import datetime
from core.memory import AbbyMemory
from core.strategy import list_strategies
from core.trading import HyperLiquidAdapter


def print_header():
    """Print application header"""
    print("=" * 60)
    print("🤖 Abby Auto Trading System")
    print("=" * 60)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def cmd_status(args):
    """Show system status"""
    print("\n📊 System Status")
    print("-" * 40)
    
    # 策略数量 - 直接列出文件
    strategy_dir = Path(__file__).parent.parent / "src" / "core" / "strategy"
    if strategy_dir.exists():
        strategies = [f.stem for f in strategy_dir.glob("*.py") 
                     if f.stem not in ['__init__', 'base', '__pycache__']]
    else:
        strategies = []
    
    print(f"   策略数量: {len(strategies)}")
    
    # 账户状态
    try:
        exchange = HyperLiquidAdapter()
        # 检查是否是模拟模式
        if hasattr(exchange, 'is_simulate') and exchange.is_simulate:
            print("   交易模式: 模拟 (paper)")
        elif hasattr(exchange, '_config') and exchange._config:
            print("   交易模式: 真实 (live)")
        else:
            print("   交易模式: 模拟 (paper)")
    except Exception as e:
        print(f"   交易模式: 未知")
    
    # 记忆状态
    try:
        memory = AbbyMemory()
        stats = memory.stats()
        print(f"   记忆数量: {stats['total']}")
    except:
        print("   记忆数量: 0")
    
    print()


def cmd_bot(args):
    """Start trading bot"""
    print("\n🚀 启动交易机器人")
    print("-" * 40)
    
    # 导入并运行机器人
    from interface import run_bot
    
    # 构建参数
    bot_args = [
        '--strategy', args.strategy or 'ma',
        '--coin', args.coin or 'BTC',
        '--interval', args.interval or '1h',
        '--mode', args.mode or 'paper',
    ]
    
    print(f"   策略: {args.strategy or 'ma'}")
    print(f"   币种: {args.coin or 'BTC'}")
    print(f"   周期: {args.interval or '1h'}")
    print(f"   模式: {args.mode or 'paper'}")
    print()
    print("   按 Ctrl+C 停止...")
    print()
    
    # 解析并运行
    sys.argv = ['run_bot.py'] + bot_args
    from interface import run_bot
    run_bot_main()


def cmd_backtest(args):
    """Run backtest"""
    print("\n📈 运行回测")
    print("-" * 40)
    print(f"   币种: {args.coin or 'BTC'}")
    print(f"   周期: {args.interval or '1h'}")
    print(f"   天数: {args.days or 30}")
    print(f"   策略: {args.strategy or 'all'}")
    print()
    
    # 使用 subprocess 从正确目录运行回测
    import subprocess
    
    auto_trading_path = '/Users/allenbot/.openclaw/workspace/project/auto-trading'
    
    # 构建命令 - 使用普通字符串避免 f-string 问题
    cmd = [
        'python3', '-c',
        '''
import sys
sys.path.insert(0, "''' + auto_trading_path + '''")
from core.backtest import Backtest

b = Backtest(
    coin="''' + (args.coin or 'BTC') + '''",
    interval="''' + (args.interval or '1h') + '''",
    days=''' + str(args.days or 30) + ''',
    use_local_data=True,
    enable_ttp=''' + str(args.ttp if hasattr(args, 'ttp') else False) + ''',
    stop_loss_pct=''' + str(args.stop_loss if hasattr(args, 'stop_loss') and args.stop_loss else 0.1) + ''',
    leverage=''' + str(args.leverage if hasattr(args, 'leverage') and args.leverage else 10) + '''
)

result = b.run_strategy("''' + (args.strategy or 'ma') + '''")
print("TRADES:" + str(result.total_trades))
print("WINRATE:" + str(result.win_rate))
print("RETURN:" + str(result.total_return))
'''
    ]
    
    process_result = subprocess.run(cmd, capture_output=True, text=True, cwd=auto_trading_path)
    
    if process_result.returncode == 0:
        output = process_result.stdout
        # 解析结果
        trades = winrate = return_pct = 0
        for line in output.split('\n'):
            if line.startswith('TRADES:'):
                trades = int(line.split(':')[1])
            elif line.startswith('WINRATE:'):
                winrate = float(line.split(':')[1])
            elif line.startswith('RETURN:'):
                return_pct = float(line.split(':')[1])
        
        print(f"\n📊 {args.strategy or 'ma'} 结果:")
        print(f"   交易次数: {trades}")
        print(f"   胜率: {winrate:.1f}%")
        print(f"   总收益: {return_pct:.1f}%")
    else:
        print(f"   ❌ 错误")
        # 只显示前几行错误
        err_lines = process_result.stderr.strip().split('\n')[:5]
        for line in err_lines:
            print(f"      {line}")
    
    print()


def cmd_memory(args):
    """Memory management"""
    print("\n💾 记忆管理")
    print("-" * 40)
    
    memory = AbbyMemory()
    
    if args.action == 'stats':
        stats = memory.stats()
        print(f"   总记忆: {stats['total']}")
        print(f"   按类型: {stats['by_type']}")
    
    elif args.action == 'search' and args.query:
        results = memory.search(args.query)
        print(f"   搜索 '{args.query}': {len(results)} 条结果")
        for r in results[:5]:
            print(f"   - {r}")
    
    elif args.action == 'list':
        all_memories = memory.list_all()
        print(f"   记忆列表 ({len(all_memories)} 条):")
        for m in all_memories[:10]:
            print(f"   - {m.get('type', 'unknown')}: {m.get('content', '')[:50]}...")
    
    print()


def cmd_list_strategies(args):
    """List all strategies"""
    print("\n📋 可用策略")
    print("-" * 40)
    
    # 直接列出文件
    strategy_dir = Path(__file__).parent.parent / "src" / "core" / "strategy"
    if strategy_dir.exists():
        strategies = [f.stem for f in strategy_dir.glob("*.py") 
                     if f.stem not in ['__init__', 'base', '__pycache__']]
        strategies.sort()
    else:
        strategies = []
    
    for i, s in enumerate(strategies, 1):
        print(f"   {i:2d}. {s}")
    
    print(f"\n   总计: {len(strategies)} 个策略")
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Abby Auto Trading CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # status 命令
    subparsers.add_parser('status', help='Show system status')
    
    # bot 命令
    bot_parser = subparsers.add_parser('bot', help='Start trading bot')
    bot_parser.add_argument('-s', '--strategy', help='Strategy name')
    bot_parser.add_argument('-c', '--coin', help='Coin symbol')
    bot_parser.add_argument('-i', '--interval', help='Time interval')
    bot_parser.add_argument('-m', '--mode', choices=['paper', 'live'], default='paper', help='Mode')
    
    # backtest 命令
    bt_parser = subparsers.add_parser('backtest', help='Run backtest')
    bt_parser.add_argument('-c', '--coin', help='Coin symbol')
    bt_parser.add_argument('-i', '--interval', help='Time interval')
    bt_parser.add_argument('-d', '--days', type=int, help='Days to backtest')
    bt_parser.add_argument('-s', '--strategy', help='Strategy name')
    bt_parser.add_argument('--ttp', action='store_true', help='Enable TTP')
    bt_parser.add_argument('--stop-loss', type=float, help='Stop loss %')
    bt_parser.add_argument('--leverage', type=int, default=10, help='Leverage')
    
    # memory 命令
    mem_parser = subparsers.add_parser('memory', help='Memory management')
    mem_parser.add_argument('action', choices=['stats', 'search', 'list'], default='stats', nargs='?')
    mem_parser.add_argument('-q', '--query', help='Search query')
    
    # strategies 命令
    subparsers.add_parser('strategies', help='List all strategies')
    
    args = parser.parse_args()
    
    print_header()
    
    if args.command == 'status':
        cmd_status(args)
    elif args.command == 'bot':
        cmd_bot(args)
    elif args.command == 'backtest':
        cmd_backtest(args)
    elif args.command == 'memory':
        cmd_memory(args)
    elif args.command == 'strategies':
        cmd_list_strategies(args)
    else:
        # 默认显示状态
        cmd_status(args)
        print("📖 使用说明:")
        print("   python main.py status        - 显示状态")
        print("   python main.py bot          - 启动机器人")
        print("   python main.py backtest     - 运行回测")
        print("   python main.py memory       - 记忆管理")
        print("   python main.py strategies  - 策略列表")
        print()


if __name__ == "__main__":
    main()
