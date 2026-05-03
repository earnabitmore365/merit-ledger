---
name: cashflow-ph1-orchestrator
description: "Know Your Cashflow Phase 1 的编排器。协调 Data Agent、UI Agent、QA Agent 完成 Phase 1 MVP 开发。包括项目初始化→数据库→服务层→组件→页面→验证的完整流水线。任何 '开始 Phase 1'、'推进记账 App'、'跑 Phase 1' 的请求必须使用此技能。也支持后续操作：'继续 Phase 1'、'重新运行某一步'、'更新进度'。"
---

# Cashflow Phase 1 Orchestrator

**执行模式:** 子代理（Sub-agent）— 使用 Agent 工具并行的 `run_in_background`

## 流水线

```
Phase 0: 上下文检查
  检查 _workspace/ 是否存在？
  ├── 存在 + 部分请求 → 跳到对应 Phase 子步骤
  ├── 存在 + 新请求 → 备份 _workspace → _workspace_prev/ → 重新执行
  └── 不存在 → 初始执行

Step 1: 项目初始化（我直接执行）
  1. npx create-expo-app cashflowAPP --template blank-typescript
  2. 安装依赖: expo-sqlite, zustand, date-fns, react-native-paper, expo-router, react-native-gesture-handler
  3. 建目录结构: src/db/ src/services/ src/stores/ src/components/ src/app/(tabs)/

Step 2: 数据库层（Data Agent）
  Agent(data-agent, subagent_type=general-purpose, model=opus)
  任务：写 src/db/schema.ts + migrations.ts + queries.ts
  验证：QA Agent 检查语法 + 边界门

Step 3: 服务层（Data Agent）
  Agent(data-agent, subagent_type=general-purpose, model=opus)
  任务：写 services/chinese-amount-parser.ts + parser.ts + tag-matcher.ts
  验证：QA Agent 检查

Step 4: 状态管理（Data Agent）
  Agent(data-agent, subagent_type=general-purpose, model=opus)
  任务：写 stores/record-store.ts + tag-store.ts
  验证：QA Agent 检查

Step 5: UI 组件（UI Agent）
  Agent(ui-agent, subagent_type=general-purpose, model=opus)
  任务：写全部 Phase 1 组件
  验证：QA Agent 检查

Step 6: 页面（UI Agent）
  Agent(ui-agent, subagent_type=general-purpose, model=opus)
  任务：写页面 + 导航布局
  验证：QA Agent 检查

Step 7: QA 完整验证
  Agent(qa-agent, subagent_type=general-purpose, model=opus)
  任务：完整跑 5 条验证标准 + 边界门 + 跨模块一致性

Step 8: Opus 审查
  调 影太极 审查全部改动
```

## 错误处理
- 每个 Step 最多重试 1 次
- 重试失败 → 记录问题到 _workspace/issues.md，继续下一步
- QA 发现的 FAIL 退回对应 Agent 修复，修复后重新 QA

## 数据传递
- 共享类型定义放在 src/types.ts
- 所有 Agent 的输出写入对应 src/ 目录文件
- QA 输出写入 _workspace/qa-{module}.md
