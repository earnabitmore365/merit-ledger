#!/bin/bash
# 自动进化 hook — PreCompact / SessionEnd 触发
# 覆盖所有项目：太极 + auto-trading

# 从 stdin 读取 hook JSON，提取 cwd
STDIN_DATA=$(cat)
CWD=$(echo "$STDIN_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null)

case "$CWD" in
  "$HOME/.claude"|"$HOME")
    LOG="/tmp/evolve_hook_taiji.log"
    nohup bash "$HOME/.claude/evolve.sh" taiji > "$LOG" 2>&1 &
    echo "🧬 evolver 已在后台启动（taiji），日志：$LOG"
    ;;
  *auto-trading*)
    LOG="/tmp/evolve_hook_auto-trading.log"
    nohup bash "$HOME/.claude/evolve.sh" auto-trading > "$LOG" 2>&1 &
    echo "🧬 evolver 已在后台启动（auto-trading），日志：$LOG"
    ;;
esac
