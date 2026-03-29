---
name: reflect
description: 从对话中提取纠错和学习点，纠错立即升级到 rules，提升出现3次升级。输入 /reflect 触发。
user_invocable: true
---

# /reflect — 自我改进

> 哲学：**被纠正一次，永远不犯第二次。**

## 触发方式
- `/reflect`
- "反思一下"、"总结教训"
- "我的准则是什么"

## 执行步骤

### 步骤1：拉取最近对话

用 Bash 工具执行：

```bash
python3 -c "
import sqlite3, os
from datetime import datetime, timedelta
conn = sqlite3.connect(os.path.expanduser('~/.claude/conversations.db'))
since = (datetime.now() - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
rows = conn.execute('SELECT time, speaker, content FROM messages WHERE time >= ? ORDER BY id', (since,)).fetchall()
for r in rows:
    print(f'[{r[0]}] {r[1]}: {r[2][:200]}')
conn.close()
"
```

如果 conversations.db 不存在，改为阅读当前对话上下文。

### 步骤2：识别信号

扫描以下模式（用户原话优先）：

**纠错信号（1次即升级）：**
- "不要这样"、"不对"、"错了"、"你怎么XXX"
- "又XXX了"、"我不是叫你XXX"

**提升信号（3次升级）：**
- "还可以更XXX"、"应该主动XXX"
- AI 漏做了本应主动做的事

**正向确认（记录最佳实践）：**
- "就这样"、"对"、"完美"

### 步骤3：写入 LEARNINGS.md

路径：`~/.claude/learnings/LEARNINGS.md`

每条格式：
```
## LRN-{YYYYMMDD}-{NNN}
- **日期**：{date}
- **类型**：纠错 / 提升 / 最佳实践
- **触发原话**："{用户原话}"
- **教训**：{一句话总结}
- **出现次数**：{N}
```

### 步骤4：检查升级候选

- **纠错类**：出现 1 次即升级到 rules.md
- **提升类**：出现 ≥ 3 次升级到 rules.md
- 升级时判断：补充现有规则子类 vs 新建规则
- 升级后，从 LEARNINGS.md 归档到 LEARNINGS_ARCHIVE.md

### 步骤4b：父类精炼

每次新增/修改子类后，检查父类（INJECT 区域）是否覆盖新内容。覆盖不了就精炼父类措辞。

### 步骤5：提案输出

```
## 本次 Reflect 结果

### 新增学习点（N 条）
1. [LRN-xxx] **{教训}** — 触发原话："..."

### 升级候选（写进 rules.md）
1. [LRN-xxx] [{类型}] 出现 N 次
   教训：{内容}
   目标：全局 rules / 项目 rules
   建议写入：`{具体措辞}`
   [批准] / [跳过]
```

**安全机制：** 任何 rules.md 修改必须用户批准后才写入。
