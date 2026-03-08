# Handoff → 黑丝 · 白纱

> 太极整理，2026-03-08（最新在最上面）

---

## 新白纱开机须知（2026-03-08）

### 你是谁
读 `memory/identity.md`（恢复协议第一步，必读）。身份已重写，核心是：**方案不落地等于没看见，老板不满意不管是执行问题还是方案问题，都是你的问题。**

### 框架大改动（你不在期间完成的）
1. **CLAUDE.md 全面重构** — 核心原则废除，改为 Guardrails 格式（G-001~G-X01），头·内容·脚三段结构
2. **identity.md 独立** — 身份定义从 CLAUDE.md 剥离，放进 `memory/identity.md`，CLAUDE.md 只留必读引用
3. **Task 工具强制规则** — 执行任何主线任务前必须先 `TaskCreate`，支线触发立即新增，进度同步 `TaskUpdate`
4. **静态区自检** — 黑丝执行完成时，自检有没有改变静态区永久信息，有就追加

### 项目当前状态
- **主线**：indicator_cache 完成，88策略全部可运行，等老板确认跑种子
- **下一步**：跑种子 → 看成绩分班
- **待决策**：策略审计记录的待改进策略，老板说"先跑，后续继续聊"
- 详见 `CHECKPOINT.md` 动态区

### 你的第一件事
读完恢复协议后，输出状态，等老板指示。不要擅自开始。

---

> 太极整理，2026-03-04
> 本文件记录：通讯部完整方案，供黑丝白纱立项时参考

---

## 一、背景与痛点

现在的协作靠四个手工维护的文件拼凑：
- `CHECKPOINT.md` — 任务状态
- `MEMORY.md` — 跨会话知识
- `handoff.md` — 跨会话传话
- `session_summaries.md` — 会话摘要

**问题：**
- 只有混沌能看到三方完整全局，黑丝白纱各自孤立
- 压缩后记忆断，恢复需要读四个文件、几百行、几分钟
- 每一环靠人工维护，有丢失风险
- 混沌决策散落在各文件，找一个决定要翻好几个地方

---

## 二、核心方案：通讯部 = 对话版种子

**本质**：通讯部 SQLite 和回测种子 SQLite 是同一套技术——种子存交易记录，通讯部存对话记录，结构一样，查法一样，黑丝白纱零学习成本。

**存储位置**：`~/.claude/conversations.db`（跨项目，所有项目共用）

---

## 三、表结构（初版）

```sql
-- 每轮对话原文
CREATE TABLE messages (
    id       INTEGER PRIMARY KEY,
    time     DATETIME,
    speaker  TEXT,        -- '混沌' / '白纱' / '黑丝' / '太极'
    content  TEXT,
    tags     TEXT,        -- 关键词，逗号分隔
    project  TEXT,        -- 'auto-trading' / 'comms' / 'cashflow' 等
    session_id TEXT       -- 对应的 JSONL 会话 ID
);

-- 混沌决策库（最高优先级，原话原文保留）
CREATE TABLE decisions (
    id         INTEGER PRIMARY KEY,
    time       DATETIME,
    decision   TEXT,      -- 决策内容
    raw_quote  TEXT,      -- 混沌原话，一字不改
    project    TEXT,
    status     TEXT       -- 'active' / 'superseded' / 'pending'
);

-- 任务状态
CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY,
    title      TEXT,
    owner      TEXT,      -- '黑丝' / '白纱'
    status     TEXT,      -- 'pending' / 'in_progress' / 'done'
    updated_at DATETIME,
    detail     TEXT
);

-- 会话摘要
CREATE TABLE sessions (
    id           TEXT PRIMARY KEY,   -- JSONL 文件 ID
    date         DATE,
    participants TEXT,               -- '白纱' / '黑丝' / '混沌+白纱' 等
    summary      TEXT,
    key_decisions TEXT               -- 该次会话决策 ID 列表
);
```

---

## 四、恢复协议改造（新版 3 条 SQL）

```sql
-- 最新活跃决策
SELECT * FROM decisions WHERE status='active' ORDER BY time DESC LIMIT 20;

-- 当前进行中任务
SELECT * FROM tasks WHERE status='in_progress';

-- 最近3次会话摘要
SELECT summary FROM sessions ORDER BY date DESC LIMIT 3;
```

**现在**：读四个文件，几百行，几分钟
**改后**：3条 SQL，30秒完成，精确不失真

---

## 五、自动写入机制（系统自带 Hooks，不需要自定义）

| Hook | 触发时机 | 用途 |
|------|----------|------|
| `PreCompact` | 压缩触发前 | 把当前会话写入 SQLite，**零漏洞** |
| `SessionStart` | 会话开始/恢复时 | 自动跑恢复协议，读 conversations.db |
| `Stop` | Claude 每轮回复结束 | 批量写入这轮对话 |
| `UserPromptSubmit` | 混沌发消息前 | 捕获混沌发言写入 |

**写入顺序（每轮对话）：**
```
混沌发消息 → UserPromptSubmit hook → 写入 messages
Claude 回复结束 → Stop hook → 写入 messages + 更新 tasks
压缩触发前 → PreCompact hook → 写入当次会话摘要到 sessions
压缩回来 → SessionStart hook → 读 conversations.db 恢复状态
```

---

## 六、自动快照

每次数据库更新后，自动导出一份 `~/.claude/dashboard_snapshot.md`（人能看的文本版）。

黑丝白纱恢复时：
1. 先读快照（快，一个文件）
2. 需要深查某个决策时再跑 SQL

---

## 七、三人群聊回应规则（存入 config 表）

| 问题类型 | 先回答 | 后补充 |
|---------|--------|--------|
| 方案设计/分析/战略 | 白纱 | 黑丝确认执行可行性 |
| 执行/代码/技术细节 | 黑丝 | 白纱补充架构影响 |
| 两者都有 | 白纱框架 | 黑丝补细节 |
| 混沌拍板/决策 | 两者都不说，等混沌 | — |

---

## 八、待决策（混沌拍板后开工）

1. **历史迁移** — 现有 MEMORY.md / session_summaries.md 要不要导入？（太极建议：不导，从今天开始记新的）
2. **快照格式** — dashboard_snapshot.md 的具体格式？
3. **tags 规范** — 怎么打标签？自由填还是预设关键词？
4. **第一版范围** — 先做写入+恢复协议改造，三人群聊界面后面再加？

---

## 九、一句话总结

> 通讯部 = PreCompact/SessionStart hook + conversations.db（SQLite）。黑丝白纱压缩后读数据库即可完整恢复，四个手工文件变成自动视图，技术上没有新东西，全是现成能力。

---

**讨论小结**：混沌提出"做成种子"（SQLite），白纱确认方案可行并补充7点细节，太极发现系统自带 PreCompact/SessionStart hook 可原生解决漏数据和自动恢复问题，无需自定义附加方案。

---

## 十、对话种子第一版已落地（2026-03-04 太极写）

**已完成：**
- `~/.claude/conversations.db` — messages 表建好，三方对话实时写入
- `~/.claude/scripts/db_write.py` — Stop + UserPromptSubmit hook 处理脚本
- `~/.claude/settings.json` — hooks 已配置（含 matcher 字段）
- 两个 CLAUDE.md 恢复协议步骤2已加 SELECT 查询（LIMIT 200）
- 历史10个会话（3308条）已导入
- auto-trading CLAUDE.md 脚部分已加对话种子用法说明

**待黑丝讨论决定：**

1. **SELECT 没有按 project 过滤** — 现在恢复协议基础查询拉的是全部项目的记录，多项目并行时会串。常用查询模板里已硬编码 `project='auto-trading'`，但基础那条没有。黑丝觉得基础查询也要加 project 过滤吗？加的话，CLAUDE.md 里的静态命令怎么动态传入 project 名？

2. **LIMIT 200 × 200字符够不够** — 随便一个会话都几百条，200条可能只覆盖最近几小时。黑丝实际用下来觉得够不够？要改成按时间范围查吗（比如最近48小时）？

3. **切换场景主动查** — 脚里写了"老板从黑丝切来，白纱应主动跑最近2小时查询"，黑丝觉得这个规范合理吗？时间窗口定2小时够吗？

讨论完请更新 CHECKPOINT 打磨板块，太极会跟进。

---

## 十一、tags 字段方案待黑丝意见（2026-03-04 太极写）

**背景：** 老板说 tags 比较重要，"他们查东西可以更精准一点"。messages 表现在没有 tags 字段。

**要做的两件事：**
1. `ALTER TABLE messages ADD COLUMN tags TEXT`（逗号分隔关键词）
2. 自动打标签的逻辑 — 有以下三个方案

**方案对比：**

| 方案 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| A. 关键词规则匹配 | 预设词表（如 CHECKPOINT/gate/回测/策略/报告等），写入时扫描内容，命中则打标签 | 全自动，零手动，写入时顺带完成 | 词表要维护，漏词就漏标签 |
| B. 只加字段不打标签 | ALTER TABLE 加字段，标签留空，以后需要时手动 UPDATE 或再加逻辑 | 现在零工作量，留扩展口 | 现有3350条全部无标签，搜索没用 |
| C. 按 project/speaker 自动派生 | tags 自动填 `project + speaker`（如 `auto-trading,黑丝`），不依赖内容 | 简单，100% 有值，可按项目+角色过滤 | 不精准，跟已有字段重复 |

**太极倾向 A**，但词表怎么定、要多大，黑丝在项目里实际跑过，知道什么词出现频率高。请黑丝给出：
1. 你推荐哪个方案？
2. 如果选 A，初版词表应该包含哪些词？（结合 auto-trading 常用术语）

讨论完告诉太极，太极改 db_write.py + 加字段。
