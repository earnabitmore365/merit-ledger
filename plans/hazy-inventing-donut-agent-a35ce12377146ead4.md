# Vibe Coding 工具调研报告
> 调研日期：2026-03-28

## 调研方法
- 8 组 WebSearch 并行搜索（覆盖 Claude Code 插件生态、GitHub workflow、spec-driven 开发、减少返工方向）
- 6 组 WebFetch 深读核心工具页面（awesome-claude-code、Ralph Loop、dev-process-toolkit、shinpr workflows、Martin Fowler SDD、claude-review-loop）

---

## 一、Claude Code Plugin Marketplace 生态（2025-2026）

### 现状
- 2025 年 10 月 Claude Code 正式推出 Plugin 系统
- 截至 2026 年 3 月，官方 marketplace 共 101 个插件：33 个 Anthropic 官方 + 68 个合作伙伴插件
- 合作伙伴涵盖：GitHub、Playwright、Supabase、Figma、Vercel、Linear、Sentry、Stripe、Firebase 等

### 插件类型三大类
1. **Skills**（技能）— 用 slash command 触发，处理特定领域任务
2. **Hooks**（钩子）— 在 Claude 生命周期节点自动触发（PreToolUse / PostToolUse / Stop）
3. **MCP Servers** — 外部连接数据库、API、文件系统

### 官方参考链接
- Anthropic 官方插件目录：https://claude.com/plugins
- Claude Code 官方文档：https://code.claude.com/docs/en/changelog

---

## 二、GitHub 上值得关注的 Claude Code Workflow 项目

### 1. awesome-claude-code（最重要的索引库）
- 链接：https://github.com/hesreallyhim/awesome-claude-code
- 性质：精选策划，非大而全堆砌
- 内容：Skills / Hooks / Slash-Commands / Agent Orchestrators / CLAUDE.md 模板 / 替代客户端
- 重点收录工具：
  - **Ralph Wiggum** — 自主迭代框架，任务→测试→修复循环
  - **AgentSys** — 任务到生产全流程自动化
  - **Auto-Claude** — 完整 SDLC 多代理框架
  - **Claude Code PM** — 带多专业代理的项目管理工作流
  - **RIPER Workflow** — Research / Innovate / Plan / Execute / Review 强制分离
  - **AB Method** — 把大问题拆成聚焦的小任务
  - **Ruflo** — 多代理 swarm 编排平台
  - **sudocode** — 轻量级代理编排工具，住在你的 repo 里

### 2. shinpr/claude-code-workflows（最完整的需求→交付流程）
- 链接：https://github.com/shinpr/claude-code-workflows
- 核心设计：按任务复杂度自动选择流程
  - 大型（6+文件）：PRD → 设计文档 → 验收标准 → 工作计划
  - 中型（3-5文件）：技术设计 → 工作计划 → 分解
  - 小型（1-2文件）：直接实现
- 专业化代理体系：requirement-analyzer / prd-creator / technical-designer / work-planner / task-decomposer / task-executor / quality-fixer / code-reviewer
- 关键命令：`/recipe-implement`、`/recipe-design`、`/recipe-diagnose`、`/recipe-fullstack-implement`

### 3. CloudAI-X/claude-workflow-v2
- 链接：https://github.com/CloudAI-X/claude-workflow-v2
- 特点：通用 workflow 插件，兼容 Claude Code / Cursor / Codex / 35+ AI agents

### 4. jeremylongshore/claude-code-plugins-plus-skills
- 链接：https://github.com/jeremylongshore/claude-code-plugins-plus-skills
- 规模：340 插件 + 1367 个 agent skills，含 CCPI 包管理器

### 5. Dev-GOM/claude-code-marketplace
- 链接：https://github.com/Dev-GOM/claude-code-marketplace
- 性质：社区驱动，Hooks / commands / agents

---

## 三、"需求→自动拆解→自动测试→自动修复"完整流程工具

### 工具 A：Kiro（AWS 出品，最成熟的 spec-driven IDE）
- 官网：https://kiro.dev/
- 定位：正式对抗 vibe coding 混乱的规范化 AI IDE
- 核心三段式流程：
  1. **requirements.md** — 用 EARS 格式写用户故事 + 验收标准
  2. **design.md** — 技术架构 / 组件 / 数据模型 / 接口
  3. **tasks.md** — 依赖顺序排列的任务清单（每个任务反向追溯到需求和设计）
- 关键特性：
  - Agent Hooks：文件保存/创建时触发，Pre Tool Use 可阻断危险操作
  - Steering Files：`.kiro/steering/` 中的持久化项目知识，不需要每次 prompt 重复说明
  - 属性化测试：从 spec 提取需求，用数百个随机用例测试
  - Checkpointing：任意步骤回滚
  - MCP 支持
- 适合场景：生产级软件，需要可维护文档，复杂特性，AWS 体系用户

### 工具 B：Ralph Loop（Claude Code 专用自主测试修复循环）
- 来源：https://www.nathanonn.com/claude-code-testing-ralph-loop-verification/
- 索引：https://awesomeclaude.ai/ralph-wiggum
- 机制：四文件系统
  - `prepare.md` — 初始化，提取测试用例，生成 status.json
  - `prompt.md` — 每轮指令：读状态 → 选测试 → 浏览器执行 → 记录 → 触发下一轮
  - `status.json` — 状态追踪（待执行/进行中/通过/失败/已知问题）
  - `results.md` — 可读日志
- 自动修复：测试失败时分析根因 → 修复 → 重测，单测试最多 3 次尝试
- 实测结果：38 个测试用例，3.5 小时全部通过，无人工干预

### 工具 C：dev-process-toolkit（强制性 TDD + 编译器门控）
- 来源：https://dev.to/nesquikm/i-built-a-claude-code-plugin-that-stops-it-from-shipping-broken-code-2gj3
- 核心洞见：AI 不擅长判断自己是否出错 → 用外部编译器做质量判断
- 四阶段流程：
  1. 理解：读 spec → 提取验收标准 → 制定计划
  2. TDD：RED→GREEN→VERIFY 循环，非零退出码=强制停止
  3. 自我审查（最多 2 轮）：第二轮发现同类问题则停止升级给人类
  4. 报告：检查清单状态 / 变更文件 / 覆盖率 / gate 结果
- 防护层：spec 约束 → 编译器 gate → 有界审查（防止 token 无限消耗）

### 工具 D：claude-review-loop（两阶段 Claude + Codex 互审）
- 链接：https://github.com/hamelsmu/claude-review-loop
- 机制：Stop Hook 拦截退出，转而触发 Codex 做独立代码审查
- 自动生成最多 4 个 Codex 子代理：差异审查 / 整体架构审查 / Next.js 专项 / UX 审查
- 输出：综合审查报告至 `reviews/review-<id>.md`
- 效果：每个任务完成前获得独立第二意见，减少返工

### 工具 E：GitHub spec-kit（GitHub 官方出品）
- 链接：https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- 流程：Constitution（架构原则）→ Specify → Plan → Tasks
- 特点：上游需要写"宪法文件"，适合团队统一规范

### 工具 F：Tessl（最激进——spec 即源码）
- Martin Fowler 分析：https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- 理念：代码文件标记 "GENERATED FROM SPEC - DO NOT EDIT"，人类只维护 spec
- 成熟度：spec-as-source 方向，最前沿但风险最高

---

## 四、减少 AI 返工 / 提高一次成功率的方法论

### 数据基准
- Claude.ai vs API：整体成功率 67% vs 49%（有 UI 加持差异）
- Claude Code vs Cursor：返工减少约 30%
- 技术团队报告开发速度提升 2-10 倍

### 关键策略（Addy Osmani LLM 工作流）
- 来源：https://addyosmani.com/blog/ai-coding-workflow/
- 原则：聚焦小任务，一次一个功能 / 一个 bug / 一个重构，每块测试通过再推进

### 实践建议（从工具研究提炼）
1. **Spec 前置**：用需求文档约束 AI 工作边界，不让 AI 自己猜意图
2. **编译器 gate**：用真实命令行结果（非 AI 自我评估）判断成功失败
3. **有界循环**：设定最大重试次数，超限升级人工，不允许无限消耗
4. **多代理互审**：一个 AI 实现，另一个 AI 审查，防止单点思维盲区
5. **插件精选原则**：4 个好插件 > 20 个"有趣"插件（官方建议）

---

## 五、工具选型对比矩阵

| 工具 | 需求拆解 | 自动测试 | 自动修复 | Claude Code 集成 | 上手难度 |
|------|----------|----------|----------|-----------------|----------|
| Kiro | ★★★★★ | ★★★★ | ★★★ | 独立 IDE，不集成 | 中 |
| shinpr/workflows | ★★★★★ | ★★★★ | ★★★★ | 原生插件 | 中 |
| Ralph Loop | ★★ | ★★★★★ | ★★★★★ | 原生，4文件即可 | 低 |
| dev-process-toolkit | ★★★★ | ★★★★★ | ★★★★ | 原生插件 | 低 |
| claude-review-loop | ★★ | ★★★ | ★★★ | Stop Hook | 低 |
| spec-kit | ★★★★★ | ★★★ | ★★ | 需配合 Claude Code | 高 |
| Tessl | ★★★★★ | ★★★ | ★★★ | 独立工具 | 高 |

---

## 六、调研空白 / 未找到的内容

1. Claude Code 官方 marketplace 中专门针对"需求→测试"的一键式插件，没有找到单一工具覆盖全流程，均为组合使用
2. "一次成功率"的量化对比数据，市面上公开数据稀少，多为定性描述
3. Tessl 的实际可用状态不明，可能仍处于 preview

---

## 七、数据来源（原始 URL）

- https://github.com/hesreallyhim/awesome-claude-code
- https://github.com/shinpr/claude-code-workflows
- https://github.com/hamelsmu/claude-review-loop
- https://github.com/CloudAI-X/claude-workflow-v2
- https://github.com/jeremylongshore/claude-code-plugins-plus-skills
- https://kiro.dev/
- https://kiro.dev/blog/introducing-kiro/
- https://kiro.dev/docs/specs/
- https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- https://www.nathanonn.com/claude-code-testing-ralph-loop-verification/
- https://dev.to/nesquikm/i-built-a-claude-code-plugin-that-stops-it-from-shipping-broken-code-2gj3
- https://addyosmani.com/blog/ai-coding-workflow/
- https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices
- https://claude.com/plugins
- https://www.morphllm.com/comparisons/kiro-vs-claude-code
