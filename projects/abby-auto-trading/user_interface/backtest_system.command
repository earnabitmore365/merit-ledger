#!/bin/bash
# Abby Auto Trading - 回测系统
# 可直接双击运行

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 启动回测系统
python3 interface/main.py backtest
