# OpenClaw Workspace 大扫除方案

## Context

Abby 的 workspace 有 120+ 个 .md 文件共 19,535 行，全部会被塞进上下文窗口。MiniMax M2.5 处理不了这么多信息，即使换了 Gemini 2.5 Flash 也会严重影响指令遵循质量。核心问题是：内容高度重复、技术细节不属于系统提示、自动生成的草稿堆积。

**目标**：将系统提示从 ~4,555 行精简到 ~500 行以内，memory 目录从 104 文件精简到 ~30 文件。

---

## 第一步：删除明确不需要的文件

| 文件 | 原因 |
|------|------|
| `BOOTSTRAP.md` (80行) | 初始化引导，文件自己写了"完成后删除" |
| `continuous-learning.md` (104行) | 2月7日的旧日志，过时了 |
| `continuous-learning-system.md` (204行) | 和上面重叠的系统说明 |
| `TOOLS.md` (94行) | 内容空洞，只有感恩表达和空模板 |
| `memory_python_learning/` 目录 | 和 memory/learning/python_learning/ 完全重复 |
| `memory/openclaw-101-guide.md` (228行) | 三个 openclaw 指南重复，只保留 deep-exploration |
| `memory/openclaw-101-deep-analysis.md` (230行) | 同上，删除 |

**预计减少**：~940 行根目录 + 458 行 memory

---

## 第二步：合并 AGENTS.md + SOUL.md + HEARTBEAT.md → 精简版

这三个文件加起来 805 行，80% 内容重复。以下内容在多个文件里出现：
- "真诚>完美, 行动>废话, 成长>正确" — 至少 6 处
- "收到任务→暂停→理解→确认→执行→验证" — 至少 4 处
- "面对错误→承认→分析→记录" — 至少 3 处
- 核心速查表 — 2 处完全相同
- 与爸爸的关系描述 — 3 处高度重叠

**方案**：
- `AGENTS.md` → 精简为唯一规则文件 (~100行)，包含：核心价值观(精简)、执行流程(一次)、安全边界、错误处理、Truth Engine
- `SOUL.md` → 精简为纯人格文件 (~50行)，只保留性格特质、做事风格、Style Guide，删除所有和 AGENTS 重复的规则
- `HEARTBEAT.md` → 精简为纯机制文件 (~40行)，只保留心跳节奏、探索模式、session 恢复步骤，删除暴富咒(20行)和所有重复规则
- `MASTER_RULES.md` (11行) → 保持不变，这个本身就是精华

**预计**：805 行 → ~190 行

---

## 第三步：MEMORY.md 大瘦身 (909行 → ~120行)

当前 MEMORY.md 混了以下不属于系统提示的内容：

| 内容 | 行数 | 处理 |
|------|------|------|
| 思维框架(暂停→理解→执行) | 1-106 | 删除，已在 AGENTS.md 里有 |
| 关于 Abby / 关于用户 | 108-128 | 删除，已在 IDENTITY.md 和 USER.md 里有 |
| HyperLiquid 地址 | 126-138 | 保留，移到精简版关键信息区 |
| 重要教训 | 140-198 | 保留精华，删除冗余描述 |
| 核心规则速查 | 200-246 | 删除，和 AGENTS.md 完全重复 |
| VWAP TTP 逻辑 + 代码 | 260-340 | 移到 memory/trading/vwap-ttp.md |
| 旧系统 vs 新系统 | 343-365 | 移到 memory/trading/ |
| Grok 哲学对话 | 368-470 | 移到 memory/grok-philosophy.md |
| 代码生成规范 | 510-681 | 移到 memory/coding-standards.md |
| 交易系统重构设计 | 684-909 | 移到 memory/trading/architecture.md |

**精简后的 MEMORY.md (~120行) 只保留**：
- 待办指引（指向 TODO.md）
- HyperLiquid 关键地址
- 重要教训精华（每条 1-2 行）
- 重要文件路径索引
- 永远不能犯的错

---

## 第四步：精简 IDENTITY.md 和 USER.md

- `IDENTITY.md` (133行) → ~60行：删除和 SOUL.md 重复的性格描述、工作原则
- `USER.md` (228行) → ~80行：删除重复的关系描述、承诺部分，保留核心用户画像

---

## 第五步：memory/ 目录整理

### 归档到 memory/_archive/（不删除，移走）
- `memory/learning/python_learning/` (15文件, 2300行) — 教材性质，不需要在上下文里
- `memory/projects/auto-exploration/` (24文件) — 2月22日一次性生成的草稿
- `memory/mcp/` (4文件, 1500行) — 参考资料性质
- `memory/refactoring/` (3文件) — 过时的重构笔记
- `memory/projects/exploration/` (17文件) — 早期探索，大部分过时
- `memory/daily/` (11文件) — 旧日记，归档保留

### 保留在 memory/
- `TODO.md` — 待办清单
- `memory/ideas/` (4文件) — 未来计划
- `memory/projects/aussie-biz-finance/` — 活跃项目
- `memory/projects/treasures/` — 爸爸的话（重要）
- 从 MEMORY.md 移出的内容：trading/, coding-standards.md, grok-philosophy.md

### 新建
- `memory/trading/vwap-ttp.md` — VWAP TTP 逻辑（从 MEMORY.md 移出）
- `memory/trading/architecture.md` — 交易系统架构（从 MEMORY.md 移出）
- `memory/coding-standards.md` — 代码生成规范（从 MEMORY.md 移出）
- `memory/grok-philosophy.md` — Grok 哲学对话（从 MEMORY.md 移出）
- `memory/_archive/` — 归档目录

---

## 第六步：清理根目录杂项

| 文件 | 处理 |
|------|------|
| `openclaw调试优化指南.md` (759行) | 移到 memory/_archive/ |
| `OpenClaw有用功能清单.md` (559行) | 移到 memory/_archive/ |
| `OpenClaw社区学习笔记.md` (347行) | 移到 memory/_archive/ |
| `小红花收藏.md` (97行) | 保留（有情感价值） |
| `SKILLS_INDEX.md` (191行) | 保留（OpenClaw 需要） |
| `mj_prompt.txt` | 保留 |
| `learning_status.txt` | 删除（过时） |

---

## 预期效果

### 根目录文件（系统提示直接加载的）

| 文件 | 之前 | 之后 |
|------|------|------|
| MEMORY.md | 909行 | ~120行 |
| AGENTS.md | 303行 | ~100行 |
| SOUL.md | 232行 | ~50行 |
| HEARTBEAT.md | 268行 | ~40行 |
| IDENTITY.md | 133行 | ~60行 |
| USER.md | 228行 | ~80行 |
| MASTER_RULES.md | 11行 | 11行 (不变) |
| SKILLS_INDEX.md | 191行 | 191行 (不变) |
| 小红花收藏.md | 97行 | 97行 (不变) |
| 其他(已删除) | 1,665行 | 0行 |
| **合计** | **4,037行** | **~749行** |

### memory/ 目录

| 类别 | 之前 | 之后 |
|------|------|------|
| 活跃文件 | 104个 | ~25个 |
| 归档文件 | 0个 | ~79个(在_archive/) |

---

## 操作顺序

1. 先创建 `memory/_archive/` 和 `memory/trading/` 目录
2. 移动需要归档的文件到 _archive/
3. 从 MEMORY.md 提取内容到新的专题文件
4. 精简 MEMORY.md
5. 精简 AGENTS.md
6. 精简 SOUL.md
7. 精简 HEARTBEAT.md
8. 精简 IDENTITY.md + USER.md
9. 删除确认不需要的文件
10. 移动根目录杂项到 _archive/

## 验证

- 确认 OpenClaw gateway 能正常加载 workspace
- 确认核心文件结构完整
- 通过 Telegram 发条消息测试 Abby 响应
