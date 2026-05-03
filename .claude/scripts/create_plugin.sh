#!/bin/bash
# ══════════════════════════════════════════════════════
# Claude Code Marketplace Plugin 打包工具
# 用法:
#   bash create_plugin.sh <name> "<description>" [--push]
#
# 示例:
#   bash create_plugin.sh haiku-gate "信用积分门卫系统" --push
#   bash create_plugin.sh my-tool "工具描述"
#
# 功能:
#   1. 在 /tmp/<name> 创建标准 marketplace 目录结构
#   2. 交互式选择要打包的文件（脚本/commands/hooks）
#   3. 生成 plugin.json, marketplace.json, hooks.json, README.md
#   4. --push: 自动 git init + gh repo create + push
# ══════════════════════════════════════════════════════

set -e

GITHUB_USER="earnabitmore365"

# ── 参数解析 ──────────────────────────────────────────

if [ $# -lt 2 ]; then
    echo "用法: bash create_plugin.sh <name> \"<description>\" [--push]"
    echo ""
    echo "示例:"
    echo "  bash create_plugin.sh haiku-gate \"信用积分门卫系统\" --push"
    exit 1
fi

NAME="$1"
DESC="$2"
PUSH=false
if [ "${3}" = "--push" ]; then
    PUSH=true
fi

WORK_DIR="/tmp/${NAME}"
VERSION="1.0.0"

echo "╔══════════════════════════════════════╗"
echo "║   Plugin 打包工具                    ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  名称: $NAME"
echo "  描述: $DESC"
echo "  目录: $WORK_DIR"
echo ""

# ── 创建目录结构 ──────────────────────────────────────

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/.claude-plugin"
mkdir -p "$WORK_DIR/scripts"
mkdir -p "$WORK_DIR/commands"
mkdir -p "$WORK_DIR/hooks"

# ── 交互式选择文件 ────────────────────────────────────

echo "═══ 选择要打包的脚本 ═══"
echo "输入脚本路径（每行一个），空行结束："
echo "  例: ~/.claude/scripts/haiku_gate.py"
echo ""

SCRIPTS=()
while true; do
    read -r -p "  脚本路径（空行结束）: " script_path
    [ -z "$script_path" ] && break
    expanded=$(eval echo "$script_path")
    if [ -f "$expanded" ]; then
        cp "$expanded" "$WORK_DIR/scripts/"
        basename=$(basename "$expanded")
        SCRIPTS+=("$basename")
        echo "    ✅ $basename"
    else
        echo "    ❌ 文件不存在: $expanded"
    fi
done

echo ""
echo "═══ 选择 slash command 文件 ═══"
echo "输入 command .md 文件路径（每行一个），空行结束："
echo "  例: ~/.claude/skills/audit/SKILL.md"
echo ""

COMMANDS=()
while true; do
    read -r -p "  command 路径（空行结束）: " cmd_path
    [ -z "$cmd_path" ] && break
    expanded=$(eval echo "$cmd_path")
    if [ -f "$expanded" ]; then
        basename=$(basename "$expanded")
        cp "$expanded" "$WORK_DIR/commands/$basename"
        COMMANDS+=("./commands/$basename")
        echo "    ✅ $basename"
    else
        echo "    ❌ 文件不存在: $expanded"
    fi
done

echo ""
echo "═══ 配置 hooks ═══"
read -r -p "  需要配置 PreToolUse hook？(y/n): " need_hooks

HOOKS_JSON='{
  "hooks": {}
}'

if [ "$need_hooks" = "y" ]; then
    read -r -p "  matcher（如 Write|Edit|Agent）: " matcher
    read -r -p "  hook 脚本文件名（如 haiku_gate.py）: " hook_script

    HOOKS_JSON=$(cat <<HEOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "$matcher",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \${PLUGIN_DIR}/scripts/$hook_script"
          }
        ]
      }
    ]
  }
}
HEOF
)
fi

echo ""
echo "═══ 额外文件 ═══"
echo "输入其他要打包的文件路径（如 docs/、模板等），空行结束："
echo ""

while true; do
    read -r -p "  文件路径（空行结束）: " extra_path
    [ -z "$extra_path" ] && break
    expanded=$(eval echo "$extra_path")
    if [ -f "$expanded" ]; then
        # 保持相对路径结构
        basename=$(basename "$expanded")
        dir=$(dirname "$expanded" | xargs basename)
        mkdir -p "$WORK_DIR/$dir"
        cp "$expanded" "$WORK_DIR/$dir/$basename"
        echo "    ✅ $dir/$basename"
    elif [ -d "$expanded" ]; then
        dir=$(basename "$expanded")
        cp -r "$expanded" "$WORK_DIR/$dir"
        echo "    ✅ $dir/ (目录)"
    else
        echo "    ❌ 不存在: $expanded"
    fi
done

# ── 生成配置文件 ──────────────────────────────────────

# commands 数组
CMD_ARRAY="[]"
if [ ${#COMMANDS[@]} -gt 0 ]; then
    CMD_ARRAY=$(printf '%s\n' "${COMMANDS[@]}" | jq -R . | jq -s .)
fi

# plugin.json
cat > "$WORK_DIR/.claude-plugin/plugin.json" <<PEOF
{
  "name": "$NAME",
  "version": "$VERSION",
  "description": "$DESC",
  "commands": $CMD_ARRAY
}
PEOF

# marketplace.json
cat > "$WORK_DIR/.claude-plugin/marketplace.json" <<MEOF
{
  "name": "$NAME",
  "owner": {
    "name": "$GITHUB_USER",
    "email": ""
  },
  "metadata": {
    "description": "$DESC",
    "version": "$VERSION"
  },
  "plugins": [
    {
      "name": "$NAME",
      "source": "./",
      "description": "$DESC",
      "category": "productivity",
      "version": "$VERSION",
      "tags": []
    }
  ]
}
MEOF

# hooks.json
echo "$HOOKS_JSON" > "$WORK_DIR/hooks/hooks.json"

# .gitignore
cat > "$WORK_DIR/.gitignore" <<GEOF
__pycache__/
*.pyc
.DS_Store
GEOF

# README.md
cat > "$WORK_DIR/README.md" <<REOF
# $NAME

$DESC

## 安装

在 Claude Code settings.json 的 \`extraKnownMarketplaces\` 中添加：

\`\`\`json
"$NAME": {
  "source": {
    "source": "github",
    "repo": "$GITHUB_USER/$NAME"
  }
}
\`\`\`

然后执行 \`claude plugins install $NAME@$NAME\`。

## 文件清单

| 文件 | 用途 |
|------|------|
$(for s in "${SCRIPTS[@]}"; do echo "| \`scripts/$s\` | 脚本 |"; done)
$(for c in "${COMMANDS[@]}"; do echo "| \`$c\` | Slash command |"; done)
| \`hooks/hooks.json\` | Hook 配置 |
REOF

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   目录结构生成完成                   ║"
echo "╚══════════════════════════════════════╝"
echo ""
find "$WORK_DIR" -not -path '*/\.git/*' -not -path '*/\.git' | sort | sed "s|$WORK_DIR|  $NAME|"

# ── 推送 GitHub ──────────────────────────────────────

if [ "$PUSH" = true ]; then
    echo ""
    echo "═══ 推送到 GitHub ═══"
    cd "$WORK_DIR"
    git init -q
    git add -A
    git commit -q -m "$NAME v$VERSION — $DESC"

    # 检查 repo 是否已存在
    if gh repo view "$GITHUB_USER/$NAME" &>/dev/null; then
        echo "  repo 已存在，force push..."
        git remote add origin "https://github.com/$GITHUB_USER/$NAME.git" 2>/dev/null || true
        git push -f origin main
    else
        gh repo create "$GITHUB_USER/$NAME" --public --source=. --push --description "$DESC"
    fi

    echo ""
    echo "  ✅ https://github.com/$GITHUB_USER/$NAME"
fi

echo ""
echo "完成。"
