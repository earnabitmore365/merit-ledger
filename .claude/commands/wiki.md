---
description: 知识库维护 — verify pre → 三步流程 → 链接检查 → verify post → commit
---

# /wiki — 知识库维护

> 铁律：**禁止猜想，一切以数据为准。**

vault 路径：`/Volumes/SSD-2TB/无极开天/`
verify 命令：`python3 /Volumes/SSD-2TB/无极开天/wuji-verify.py`

**用法**：
```
/wiki add <主题>   → 添加新知识
/wiki fix <主题>   → 修正/更新现有页面
/wiki              → 无参数，扫 _incoming.md 找待处理条目
```

---

## 知识流动三步（每次开工先判断走哪步）

```
外部来源（调研/对话/事件）
  → Step A: 存 raw/（原始，只进不改）
  → Step B: 提炼进分区（技术/踩坑/堂规/项目等）
  → Step C: 写知识库条目（结论速查，AI 第一眼看到答案）

纯内部整理（规则调整/已有知识更新）
  → 直接 Step B + Step C，跳过 Step A

对话沉淀（与 agent 的讨论/决策）
  → 跳过 Step A（对话种子已自动存入 raw/conversations/）
  → Step B + Step C，sources 直接指向对话种子路径
  → tags 标记所属项目和领域，如 domain/auto-trading、domain/pine-mcp
```

**raw 写什么**：外部资料、调研原文、对话记录、踩坑现场。
**分区写什么**：提炼后的知识，有结构有上下文。
**知识库写什么**：一句话结论 + 来源链接，AI 速查用。

---

## 开工前：建 Task Tracker

用 TaskCreate 为每个 Phase 建 task：

- Phase 0：verify --pre
- Step A（如需）：raw 存档（对话沉淀跳过，种子已自动存入）
- Step B：写/改分区页面
- Step C：写知识库条目
- Phase 3：链接检查
- Phase 4：verify --post
- Phase 5：Opus 结构审（按需）
- 完成：摘要

**每个 Phase 完成时用 TaskUpdate 改状态为 completed。**
**未 completed 的 task = 没做完，不能跳。**

---

## Phase 0：verify --pre

```bash
python3 /Volumes/SSD-2TB/无极开天/wuji-verify.py --pre
```

记录基线 ❌ 数。有 ❌ 先修，再继续。

✅ 完成后：TaskUpdate Phase 0 → completed，再进 Phase 1。

---

## Phase 1：查重 + 定位

先查库确认不重复：

```bash
grep -r "关键词" /Volumes/SSD-2TB/无极开天 --include="*.md" -l \
  --exclude-dir=".archive" --exclude-dir="raw"
```

命中 → 改为 fix 模式，不新建。
没命中 → 确定分区：

| 分区 | 内容 | 路径 |
|------|------|------|
| 世界观 | 创世/存在/根基哲学 | `世界观/` |
| 历史 | 关键事件/版本演变/辩论 | `历史/` |
| 堂规 | 宪法/身份/制度/流程/阴阳制衡 | `堂规/` |
| 项目 | 各项目架构知识 | `项目/` |
| 踩坑 | 教训，提炼后的知识 | `踩坑/` |
| 技术 | 跨项目技术（外部工具/API）| `技术/` |
| 词典 | 术语权威定义 | `词典/` |
| 决策 | 重大架构决策 ADR | `决策/YYYY-MM-DD-主题.md` |
| 知识库 | 结论优先速查条目 | `知识库/` |

分区不确定 → 直接进 Phase 5（调 Opus 决定位置），再回来建文件。

✅ 完成后：TaskUpdate Phase 1 → completed，再进 Step A / Step B。

### 无参数模式

```bash
cat /Volumes/SSD-2TB/无极开天/_incoming.md | grep "\- \[ \]" | head -20
```

从未处理条目里挑一条开始，走 fix 模式。

---

## Step A：raw 存档（有外部来源时）

raw 目录分工：

| 内容类型 | 目录 |
|---------|------|
| 老祖原话、重要对话 | `raw/conversations/` |
| Opus/三方探讨全文 | `raw/discussions/` |
| 踩坑现场、错误案例 | `raw/incidents/` |
| 架构决策原始素材 | `raw/decisions/` |
| 外部资料（第三方文档）| `raw/external/文档/` |

**命名**：`YYYY-MM-DD-主题关键词.md`
**铁律**：raw 文件只进不改，只能 append 或新建。

> **对话沉淀捷径**：对话种子已自动存入 `raw/conversations/<项目>/YYYY-MM-DD.md`。
> 不需要手动建 raw 文件，sources / 原典 直接指向对话种子即可。
> 通过 tags 标记所属项目（`domain/auto-trading`）和领域（`domain/pine-mcp`）。

✅ 完成后：TaskUpdate Step A → completed，再进 Step B。

---

## Step B：写/改分区页面

### 新建文件模板

```markdown
---
id: <分区>-<文件名>
tags:
  - scope/全员
  - domain/<领域>
aliases:
  - <别名>
sources:
  - raw/<路径>/<文件名>.md          # 有原始文档时
  - raw/conversations/<项目>/YYYY-MM-DD.md  # 对话沉淀时（跳过手动写raw）
confidence: medium
updated: YYYY-MM-DD
---

# 标题（即触发条件）

> 一句话概括。

## 结论

（祈使句，用"必须/禁止/永远"，不用"建议"）

## 为什么

（事件/来源，一句话）

## 相关

- [[链接1]] — 说明

> 原典：[[raw/<路径>/<文件名>]]     # 对话沉淀：[[raw/conversations/<项目>/YYYY-MM-DD]]
```

### 写作规则

1. **先结论后细节** — 最重要内容放最前
2. **查表优先** — 用表格不用长段落
3. **出链必须有** — `## 相关` 至少 1 条 wikilink
4. **原典标注** — 有 raw/ 来源时底部加 `> 原典：[[raw/...]]`
5. **confidence** — high（有实证）/ medium（有推断）/ low（存疑）
6. **updated** — 当天日期

✅ 完成后：TaskUpdate Step B → completed，再进 Step C。

---

## Step C：写知识库条目

知识库 = AI 速查层，格式比分区页面更精简：

```markdown
---
id: 知识库-<主题>
tags:
  - scope/全员
  - trigger/<触发场景>
  - domain/<领域>
aliases:
  - <别名>
sources:
  - raw/<路径>.md
confidence: medium
updated: YYYY-MM-DD
---

# 遇到 X 时 / 做 X 前

> 一句话结论。

## 结论

**祈使句，直接给答案。**

## 为什么

一句话说来源事件。

## 相关

- [[分区/对应详细页面]] — 完整版
```

**知识库条目什么时候写**：
- 这个结论 AI 会反复查 → 写
- 分区页面太长，AI 需要先看答案 → 写
- 纯参考资料，不需要速查 → 不写，留分区页面即可

✅ 完成后：TaskUpdate Step C → completed，再进 Phase 3。

---

## Phase 3：链接检查

**每次写/改完必过，不能跳。**

**Step 1 — 检查新文件有没有入链（add 模式必做）**

```bash
FNAME="<文件名不带.md>"
grep -r "$FNAME" /Volumes/SSD-2TB/无极开天 --include="*.md" \
  --exclude-dir=".archive" -l
```

结果为 0 → 必须在至少 1 个相关页面的 `## 相关` 里加链接，不允许孤立节点上线。

**Step 2 — 检查出链有没有断链（两步都过才算 Phase 3 完成）**

```bash
python3 -c "
import re, os, sys
page = sys.argv[1]
vault = '/Volumes/SSD-2TB/无极开天'
content = open(page).read()
links = re.findall(r'\[\[([^\]#|]+)', content)
broken = []
for link in links:
    link = link.strip()
    candidates = [
        os.path.join(vault, link + '.md'),
        os.path.join(vault, link, 'README.md'),
    ]
    if not any(os.path.exists(c) for c in candidates):
        result = os.popen(f'find \"{vault}\" -name \"{os.path.basename(link)}.md\" 2>/dev/null').read()
        if not result.strip():
            broken.append(link)
if broken:
    print('❌ 断链：')
    for b in broken: print(f'  {b}')
else:
    print('✅ 无断链')
" <改动文件的完整路径>
```

✅ 完成后：TaskUpdate Phase 3 → completed，再进 Phase 4。

---

## Phase 4：verify --post

```bash
python3 /Volumes/SSD-2TB/无极开天/wuji-verify.py --post
```

对比基线，逐条处理报警：

| 报警类型 | 处理 |
|---------|------|
| 知识库真问题（断链/格式错/分层错） | 当场修 |
| verify 配置过时 | 维护 verify 配置，不能标遗留 |

修完重跑，直到 ✅ 全部通过。

✅ 完成后：TaskUpdate Phase 4 → completed，再进 Phase 5。

---

## Phase 5：Opus 结构审（按需触发）

**触发条件（满足任一就调）：**
- 新文件的分区位置不确定
- 堂规/世界观级别的内容修改（影响全局认知）
- 不知道哪些现有页面应该反向链接

**不调条件：**
- 普通技术文档/踩坑/决策更新
- 只是修了格式或补了 wikilink

**Prompt 模板：**

```
你是影太极，这是一次【协助型】调用，不要自己动手。

我刚刚写/改了：[文件路径]
内容主题：[一句话描述]
当前放在：[分区/目录]

请分析：
1. 分区位置合适吗？有没有更合适的位置？
2. 哪些现有页面应该反向链接到这个页面？
3. 出链（## 相关）有没有明显遗漏？

不要自己动手，告诉我该怎么改。
```

✅ 完成后：TaskUpdate Phase 5 → completed（或标注"不适用/已跳过"），再进完成摘要。

---

## 完成摘要

```
📚 知识库维护完成
   Step A raw：[对话种子 / 新建 raw / 无]
   Step B 分区：[改了哪些文件]
   Step C 知识库：[新建了哪些条目 / 无]
   孤立检查：✅ 无孤立节点 / ❌ [处理情况]
   verify：✅ 无新增违规
   遗留：[诚实列出，没有则写"无"]
```

> vault 使用 obsidian-git 管理 commit，不需要手动 git 操作。
