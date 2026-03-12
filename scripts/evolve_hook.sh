#!/bin/bash
# 自动进化 hook — PreCompact / SessionEnd 触发
# 只处理 taiji（auto-trading 由项目级 hook 独立处理）

# 从 stdin 读取 hook JSON，提取 cwd
STDIN_DATA=$(cat)
CWD=$(echo "$STDIN_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null)

# 只处理 taiji
if [ "$CWD" = "$HOME/.claude" ]; then
  LOG="/tmp/evolve_hook_taiji.log"
  nohup bash "$HOME/.claude/evolve.sh" taiji > "$LOG" 2>&1 &
  echo "🧬 evolver 已在后台启动（taiji），日志：$LOG"
fi
