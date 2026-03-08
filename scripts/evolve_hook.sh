#!/bin/bash
# 自动进化 hook — PreCompact / SessionEnd 触发
# 后台跑，不阻塞主会话

CWD="${1:-$(pwd)}"
HOME_DIR="$HOME"

# 按 cwd 判断项目
if [ "$CWD" = "$HOME_DIR/.claude" ]; then
  PROJECT="taiji"
elif [ "$CWD" = "$HOME_DIR/project/auto-trading" ]; then
  PROJECT="auto-trading"
else
  # 不在管理的项目里，不跑
  exit 0
fi

LOG="/tmp/evolve_hook_${PROJECT}.log"
nohup bash "$HOME_DIR/.claude/evolve.sh" "$PROJECT" > "$LOG" 2>&1 &

echo "🧬 evolver 已在后台启动（$PROJECT），日志：$LOG"
