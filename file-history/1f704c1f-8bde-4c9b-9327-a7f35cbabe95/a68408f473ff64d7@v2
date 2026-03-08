#!/bin/bash
# 太极级 — 自进化启动脚本
# 用法：
#   bash ~/.claude/evolve.sh                          # 跑一次，生成 GEP prompt
#   bash ~/.claude/evolve.sh auto-trading             # 指定项目（默认 auto-trading）
#   EVOLVE_STRATEGY=repair-only bash ~/.claude/evolve.sh  # 只修bug

set -e

PROJECT="${1:-auto-trading}"
PROJECT_DIR="/Users/allenbot/project/$PROJECT"
EVOLVER_DIR="$HOME/.claude/tools/evolver"
EVOLVER_WORKSPACE="$HOME/.claude/evolver"

# 切到项目根目录（让 evolver 找到 .git 确认 repo root）
cd "$PROJECT_DIR"

# 运行 evolver，workspace 在 ~/.claude/evolver/
MEMORY_DIR="$EVOLVER_WORKSPACE" \
OPENCLAW_WORKSPACE="$EVOLVER_WORKSPACE" \
EVOLVER_REPO_ROOT="$PROJECT_DIR" \
node "$EVOLVER_DIR/index.js" run "${@:2}"

# 输出最新 GEP prompt 路径
LATEST=$(ls -t "$EVOLVER_WORKSPACE/evolution/gep_prompt_"*.txt 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "GEP Prompt 已生成：$LATEST"
  echo "黑丝用以下命令读取："
  echo "  cat \"$LATEST\""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
