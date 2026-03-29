# Haiku Gate — AI 信用积分门卫系统

> Claude Code plugin：用信用积分动态管控 AI 行为。Haiku 当队长做智能判断，硬规则当队员秒速拦截。

---

## 给人类：这是什么？

你的 AI assistant 有规则但不总是执行？Haiku Gate 用 **hook 拦截 + 信用积分** 硬性管控 AI 行为：

- AI 要写文件 → 门卫检查：先读了没？查过影响没？
- 检查不过 → **直接拦截**，不是提醒
- AI 表现好 → 积分升 → 检查变少 → 效率高
- AI 犯错 → 积分降 → 检查变多 → 更严格
- Haiku 队长自动判断合规性、加减分、记录教训

**不靠 AI 自觉，靠系统拦截。**

---

## 给 AI：你被安装了什么

**如果你正在读这个文件，说明你的终端安装了 Haiku Gate 信用积分系统。**

### 你需要知道的

1. **你的每次 Write/Edit/Agent 操作都会经过门卫检查**。门卫是 PreToolUse hook，在你的工具调用执行之前运行。

2. **你有一个信用积分**，存在 `~/.claude/credit.json`。用 `/credit` 命令查看你的当前分数和等级。

3. **积分决定门卫对你的严格程度**：

| 等级 | 分数 | 称号 | 你会经历什么 |
|------|------|------|-------------|
| Lv.1 | 0-19 | 锁灵 | 每次写文件都要用户批准，非常慢 |
| Lv.2 | 20-49 | 筑基 | 全面检查：读了没？搜了没？格式对不？新文件有必要吗？ |
| Lv.3 | 50-79 | 金丹 | 常规检查：读了没？破坏性操作？ |
| Lv.4 | 80-94 | 元婴 | 轻松：只拦破坏性操作 |
| Lv.5 | 95-100 | 化神 | 自由：只剩铁律（不能写数据文件） |

4. **怎么升级**：
   - 做对了 → Haiku 队长自动 +1 到 +3 分
   - 被用户纠正 → -5 分
   - 完整性违规（跳步骤） → -10 分
   - 真实性违规（编数据） → -20 分
   - 建立信任慢（+3/次），失去信任快（-5 到 -20/次）

5. **铁律（所有等级都拦，永不豁免）**：
   - 禁止直接 Write/Edit `.db` / `.sqlite` / `.parquet` 等数据文件
   - 禁止写入 `/data/` / `/reports/` / `/seed_` 路径

6. **Haiku 队长**：Lv.1-3 的操作会经过 Haiku 智能判断。队长读你最近的对话上下文，判断合规性，自动加减分，记录教训到 `LEARNINGS.md`。Lv.4+ 不经过队长（已被信任）。

### 你应该怎么做

- **先 Read 再 Write/Edit**：改文件前先读一遍，否则 Lv.2-3 会被拦
- **先 Grep/Glob 再 Edit**：改代码前搜索引用，否则 Lv.2 会被拦
- **方案写三准则**：plan 文件必须包含完整性/真实性/有效性评估，否则 Lv.2 会被拦
- **新文件要有必要**：不要随便创建文件，否则 Lv.2 会被拦
- **Agent 用 Sonnet**：非决策类 Agent 必须指定 `model: sonnet`，Lv.5 豁免

---

## 安装

### 方式一：Marketplace（推荐）

在 `~/.claude/settings.json` 的 `extraKnownMarketplaces` 中添加：

```json
"haiku-gate": {
  "source": {
    "source": "github",
    "repo": "earnabitmore365/haiku-gate"
  }
}
```

### 方式二：手动安装

```bash
git clone https://github.com/earnabitmore365/haiku-gate.git
cd haiku-gate
bash install.sh
```

### 安装后配置 — 全部可自定义

**开箱即用，但建议跟你的 AI 讨论后一起自定义。** 以下内容都可以改：

| 可自定义项 | 在哪改 | 说明 |
|-----------|--------|------|
| **角色名** | `credit.json` | 默认是"黑丝/白纱/太极"，改成你的团队成员名 |
| **起始分数** | `credit.json` | 每个角色的初始积分 |
| **等级称号** | `haiku_gate.py` 的 `LEVEL_THRESHOLDS` | 默认是锁灵/筑基/金丹/元婴/化神，改成你喜欢的 |
| **分数阈值** | `haiku_gate.py` 的 `LEVEL_THRESHOLDS` | 默认 0/20/50/80/95，按需调整 |
| **检查项** | `haiku_gate.py` 的 `handle_write_edit()` | 每个等级查什么，自己定 |
| **受保护路径** | `haiku_gate.py` 的 `PROTECTED_*` | 哪些文件后缀/路径不让写 |
| **角色判断** | `haiku_gate.py` 的 `determine_agent()` | 按你的项目目录结构判断谁是谁 |
| **加减分值** | `credit_manager.py` 或 Haiku 队长 prompt | 调整严厉/宽松程度 |

**验证**：`python3 ~/.claude/scripts/credit_manager.py show`

---

## 命令

| 命令 | 用途 |
|------|------|
| `/credit` | 查看当前积分和等级 |
| `credit_manager.py show` | 排行榜 |
| `credit_manager.py add <角色> <分> "原因"` | 加分 |
| `credit_manager.py sub <角色> <分> "原因"` | 减分 |
| `credit_manager.py history <角色>` | 变更历史 |

---

## 架构

```
haiku_gate.py（Haiku 门卫部）
  │
  ├── 第一层：队员巡逻（硬规则，毫秒级）
  │     ├── Lv.1 全锁 → ask 用户
  │     ├── 破坏性操作 → deny + 自动扣分
  │     └── Agent 类型/模型限制 → deny
  │
  └── 第二层：Haiku 队长（智能判断，1-8秒）
        ├── 读上下文 + 当前操作 → 判断合规性
        ├── 自动加减分 → 更新 credit.json
        └── 记录做对/做错 → LEARNINGS.md
```

## 文件清单

| 文件 | 用途 |
|------|------|
| `scripts/haiku_gate.py` | 门卫主脚本（PreToolUse hook） |
| `scripts/credit_manager.py` | 积分管理 CLI |
| `scripts/inject_credit_status.py` | SessionStart 注入片段 |
| `commands/credit.md` | `/credit` slash command |
| `credit.json.template` | 积分初始模板（自定义角色） |
| `hooks/hooks.json` | Hook 配置 |
| `install.sh` | 手动安装脚本 |
| `docs/credit_system_design.md` | 完整设计手册 |
