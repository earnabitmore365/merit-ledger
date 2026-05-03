#!/bin/bash
# 自动同步 reforge 源文件到 GitHub repo 并推送
# 触发：PostToolUse hook 检测到 reforge 文件改动

REPO="$HOME/projects/reforge"
SRC_SKILL="$HOME/.claude/commands/reforge.md"
SRC_CTX="$HOME/.claude/merit/reforge_context.py"

# 复制源文件到 repo
cp "$SRC_SKILL" "$REPO/commands/reforge.md" 2>/dev/null
cp "$SRC_CTX" "$REPO/scripts/reforge_context.py" 2>/dev/null

cd "$REPO" || exit 1

# 有变更才推
if git diff --quiet && git diff --cached --quiet; then
    exit 0
fi

ts=$(date "+%Y-%m-%d %H:%M")
git add -A
git commit -m "auto-sync $ts" >/dev/null 2>&1
git push >/dev/null 2>&1 &
