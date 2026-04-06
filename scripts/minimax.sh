#!/bin/bash
# 用 MiniMax M2.7-highspeed 启动 Claude Code（不消耗 Anthropic 配额）
# 用途：Ralph Loop、Agent Evolution 等非核心任务
#
# 用法：
#   bash ~/.claude/scripts/minimax.sh              # 交互模式（跑 /ralph 等）
#   bash ~/.claude/scripts/minimax.sh -p "prompt"  # headless 模式

ANTHROPIC_BASE_URL="https://api.minimax.io/anthropic" \
ANTHROPIC_API_KEY="$(cat ~/.claude/.minimax_key)" \
claude --model MiniMax-M2.7-highspeed "$@"
