# Plan: 已完成 — Evolver Hook 链路自审修复 + Autoresearch 调研（暂不动 evolver）

## Context

老板要求确保黑丝选 "clear context"（选1）时 evolver 自动跑。完整盘查+验证，2 个需修复，2 个已确认无问题。

## 盘查结果

### 链路图（两条入口）

```
【太极】 PreCompact/SessionEnd
  → 全局 ~/.claude/settings.json
  → evolve_hook.sh
  → evolve.sh taiji

【黑丝】 PreCompact/SessionEnd
  → 项目级 ~/project/auto-trading/.claude/settings.json
  → 直接 nohup bash evolve.sh auto-trading（绕过 evolve_hook.sh）
```

### 问题清单

| # | 问题 | 状态 |
|---|------|------|
| 1 | **锁在错误位置**：锁在 `evolve_hook.sh`，项目级 hooks 绕过它直接调 `evolve.sh`，无并发保护 | ⚠️ 需修复 |
| 2 | **`evolve_hook.sh` 的 auto-trading case 多余**：项目级 hooks 已直接处理，全局的 case 永远不会被触发 | ⚠️ 需清理 |
| 3 | ~~SSD 路径不匹配~~ — 已验证 inode 相同（159），`~/project/auto-trading` = `/Volumes/BIWIN NV 7400 2TB/project/auto-trading` | ✅ 无问题 |
| 4 | ~~"clear context" 触发什么事件~~ — 已验证：创建新 JSONL（`57b54b31`→`de9bcf08`），确认触发 **SessionEnd**（可能同时触发 PreCompact），evolver 确定会跑 | ✅ 已确认 |

## 改动

### 1. `~/.claude/evolve.sh` — 加锁

在 `set -e` 之后、项目参数解析之前（第 8 行）插入：

```bash
# 并发锁：防止 PreCompact + SessionEnd 同时触发
LOCKFILE="/tmp/evolve.lock"
if [ -f "$LOCKFILE" ]; then
  LOCK_PID=$(cat "$LOCKFILE" 2>/dev/null)
  if kill -0 "$LOCK_PID" 2>/dev/null; then
    echo "⏭️ evolver 已在运行（PID $LOCK_PID），跳过"
    exit 0
  fi
  rm -f "$LOCKFILE"
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT
```

所有入口（全局 hook、项目级 hook）都经过 `evolve.sh`，锁在这里 = 全覆盖。

### 2. `~/.claude/scripts/evolve_hook.sh` — 简化

去掉 auto-trading case 和锁逻辑（锁已移到 evolve.sh），只保留太极：

```bash
#!/bin/bash
# 自动进化 hook — PreCompact / SessionEnd 触发（全局级）
# auto-trading 由项目级 hooks 直接调 evolve.sh，不经过此文件

STDIN_DATA=$(cat)
CWD=$(echo "$STDIN_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null)

case "$CWD" in
  "$HOME/.claude"|"$HOME")
    LOG="/tmp/evolve_hook_taiji.log"
    nohup bash "$HOME/.claude/evolve.sh" taiji > "$LOG" 2>&1 &
    echo "🧬 evolver 已在后台启动（taiji），日志：$LOG"
    ;;
esac
```

## 验证步骤

1. 模拟并发：同时启动两个 `bash evolve.sh auto-trading`，确认第二个被锁跳过
2. `echo '{"cwd":"/Users/allenbot"}' | bash evolve_hook.sh` — 太极正常触发
3. 确认项目级 hooks 调 `evolve.sh auto-trading` 正常运行且受锁保护
