# Fix: evolve.sh SESSIONS_DIR 路径不匹配

## Context

`~/project` 是符号链接 → `/Volumes/BIWIN NV 7400 2TB/project`。evolve.sh 用 `$HOME/project/$PROJECT` 编码路径得到 `-Users-allenbot-project-auto-trading`，但黑丝白纱的 Claude Code 解析了符号链接，JSONL 写入 `-Volumes-BIWIN-NV-7400-2TB-project-auto-trading`。导致 evolver 读的是错误目录（里面只有 Abby 聊天和一个旧会话，共 ~24MB 垃圾数据）。

## 修复

**文件：** `~/.claude/evolve.sh`（第 36 行）

```bash
# 原来：
REPO_ROOT="$HOME/project/$PROJECT"

# 改成：
REPO_ROOT=$(readlink -f "$HOME/project/$PROJECT")
```

### 影响链（全部自动修正，不需要额外改动）
- 第 37 行 PROJECT_ENCODED：从 REPO_ROOT 派生 → 自动正确
- 第 38 行 SESSIONS_DIR：从 PROJECT_ENCODED 派生 → 自动正确
- 第 41 行 cd "$REPO_ROOT"：带空格路径已有双引号 → 安全
- 第 60/90 行 EVOLVER_REPO_ROOT：用 $REPO_ROOT → 自动正确
- 第 61 行 AGENT_SESSIONS_DIR：用 $SESSIONS_DIR → 自动正确
- 第 85 行 mkdir/cp：带空格路径已有引号 → 安全
- taiji 分支（32-34行）：不走 else 分支 → 不受影响
- evolve_hook.sh：只传 "taiji" 字符串 → 不受影响

### 已验证
- macOS `readlink -f` 可用（退出码 0）
- 非符号链接路径 readlink -f 返回原路径（无副作用）
- set -e 兼容（路径不存在才会报错，这是正确行为）

## 验证步骤

修改后执行：
```bash
# 1. 确认编码结果
source <(grep -A3 "^else" ~/.claude/evolve.sh | head -3) 2>/dev/null
# 或直接：
echo $(readlink -f "$HOME/project/auto-trading" | sed 's|/|-|g')
# 期望输出：-Volumes-BIWIN-NV-7400-2TB-project-auto-trading

# 2. 确认 SESSIONS_DIR 目录存在且有黑丝白纱的 JSONL
ls ~/.claude/projects/-Volumes-BIWIN-NV-7400-2TB-project-auto-trading/*.jsonl | wc -l
# 期望：50+ 个文件
```
