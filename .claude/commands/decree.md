---
description: 奉令 — 读任务，路由到正确 skill，然后执行
---

# /decree — 奉令

> 诏令已下，奉令而行。
> 先判断类型，再选 skill，然后执行。
> 发现任务有歧义 → 停下问老祖，不自行解决。

---

## 开工前：建 Task Tracker（第一件事，不跳）

用 TaskCreate 工具建任务，建完再开始：

- Phase 0：理解任务 + 路由判断
- Phase 1-N：执行（由选定 skill 展开，执行时再拆细）

每个 Phase 完成时用 TaskUpdate 改状态为 completed。
**未 completed 的 task = 没做完，不能跳。**

---

## Phase 0：理解任务

### 1. 读任务内容

任务来源：
- 老祖 / 执事直接说的
- handoff 文件（读完整内容）
- plan 文件（读完整内容）

### 2. 路由判断

读完任务后，按以下表格判断用哪个 skill：

| 任务类型 | 判断标准 | Skill |
|---------|---------|-------|
| 代码新建 | 新功能 / 新工具 / 从零开始 | `/forge` |
| 代码修复 | 修 bug / 审查 / 重构 / 清理 | `/reforge` |
| 知识/认知 | 调研 / 文档 / 配置 / 知识库 / 世界观更新 | `/wiki` |
| 混合任务 | 既改代码又有新知识沉淀 | `/forge`（forge Phase 5 自带回写知识库） |
| 判断不清楚 | 任务类型模糊，无法归类 | **停下问老祖** |

### 3. 列出执行计划

路由确定后，把任务拆成具体步骤：

```
使用 Skill：[forge / reforge / wiki]
原因：[一句话说明为什么选这个]

Phase 1：[描述]
  改动文件：[列出]
  改动内容：[简述]

Phase 2：[描述]
  ...
```

### 4. 确认后再动手

列出计划后向老祖确认：**理解正确后才进入执行，不抢跑。**

✅ 确认后：TaskUpdate Phase 0 → completed，再进执行阶段。

---

## Phase 1 - Phase N：执行

按选定 skill 的完整流程执行：

**`/forge`**（改代码 - 新建）
- Phase 0: verify --pre → Phase 1: 查库读文档 → Phase 2: 实施 → Phase 3: verify --post → Phase 4: Opus 审 → Phase 5: commit + 回写知识库

**`/reforge`**（改代码 - 修复/审查）
- Phase 0: verify --pre → Phase 1: 4 agent 审查 → Phase 2: 美容 → Phase 3: Opus 审 → Phase 4: verify --post → Phase 5: commit

**`/wiki`**（改认知 - 知识库/文档/世界观）
- Phase 0: verify --pre → Phase 1: 查重定位 → Phase 2: 写/改 → Phase 3: 链接检查 → Phase 4: verify --post → Phase 5: Opus 结构审（按需）→ Phase 6: commit

选定 skill 完整执行完毕后：

✅ 完成后：TaskUpdate Phase 1-N → completed。通知执事审查，等 PASS 才算交活。

---

## 规则

- 任务文件是诏令，不质疑，不擅自修改范围
- 路由判断不清楚 → 停下问，不猜
- 理解清楚再动手，不抢跑
- 完成后通知执事审查，等 PASS 才算交活

---

## 案例积累区

> 遇到路由边界案例，把判断结果记在这里，积累后提炼成规则。

| 日期 | 任务描述 | 判断结果 | 原因 |
|------|---------|---------|------|
| （待积累）| | | |
