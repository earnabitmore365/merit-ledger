# stone_guard 文档更新 v7→v8

## Context

stone_guard_v7_design.md 在这个会话里重写过一次，但后续又做了大量改动（评分 v8 三律二法重设计、文件锁、通道按角色分开、CHANGELOG 提醒改自写、penalty_only 到期自动解除等），文档已过时。需要同步到最新状态。

## 步骤

### 1. 调研（只读，不改文件）
- [ ] 读当前 `stone_guard_v7_design.md`，逐节标注过时内容
- [ ] 读 `merit_gate.py` 结构索引（L12-44），确认最新行号和功能列表
- [ ] 读 `EVOLVE_README.md`，确认自进化系统描述
- [ ] `ls ~/.claude/merit/` 列出所有文件，对比文档里的文件清单

### 2. 修改文档
- [ ] 标题从 v7 改为 v8
- [ ] **评分系统**：SCORING_TABLE 更新（routine_complete=0、complete_no_correction=+2），语气识别改 MiniMax，自审从 +5 改 +1
- [ ] **文件锁**：update_credit 用 fcntl.flock，credit_manager 的 mission_done/abort 也加锁
- [ ] **CHANGELOG**：PostToolUse 记录操作 → Stop 提醒 AI 自写（不是 MiniMax 代写），按角色分开
- [ ] **通道**：channel_check 按角色分开（channel_check_太极.json / channel_check_两仪.json），消息存 channel_reminder.txt → UserPromptSubmit 注入
- [ ] **penalty_only**：支持永久（until=null）/ 定时（until=ISO时间）/ 到期自动解除
- [ ] **自进化**：evolve.py cron 每5分钟独立运行、子类只增不减、父类只追加不重写、二次审查、规则质量精炼
- [ ] **架构文件清单**：补 EVOLVE_README.md、tests/、channel_check_*.json、pending_changelog_ops_*.jsonl、channel_reminder.txt、changelog_reminder.txt 等新增文件
- [ ] **宪法引用**：确认文档里的宪法描述是三律二法（不是旧四关）

### 3. 验证四件套
- [ ] `python3 -m py_compile` — 如果改了 .py 文件
- [ ] `python3 ~/.claude/merit/verify.py stone_guard_v7_design.md` — 跑 verify 确认无 ❌
- [ ] **全链路**：grep "stone_guard" 确认 MEMORY.md / CLAUDE.md 的引用路径一致
- [ ] **文档一致性**：文档里的文件清单 vs `ls ~/.claude/merit/` 实际文件，逐个对比

### 4. Sonnet Code Review
- [ ] 派 Sonnet 跑 code-review 审查改动（`Agent model: sonnet`）
- [ ] 审查结果有 Critical/Major 问题 → 修完再继续
- [ ] 审查无问题 → 继续

### 5. 更新 CHANGELOG
- [ ] 在 `memory/CHANGELOG.md` 追加本次改动记录
- [ ] 格式：`### HH:MM 一句话描述做了什么和为什么 (YYYY-MM-DD)`

### 6. 自审（三律二法）
- [ ] ✅ 完整：文档每一节都对照了代码实际状态
- [ ] ✅ 真实：文件清单与 ls 一致，行号与 grep 一致
- [ ] ✅ 有效：只更新过时内容，没有多余改动
- [ ] ✅ 知常：文档是给恢复后的 AI 看的，必须准确反映当前系统
- [ ] ✅ 静制动：先调研完再改，不边看边改

### 7. 汇报执事
- [ ] 附自审结果 + 遗留清单
- [ ] 如果有 backlog 变化，同步更新 backlog.md

## 关键文件

| 文件 | 作用 |
|------|------|
| `~/.claude/projects/-Users-allenbot/memory/stone_guard_v7_design.md` | 要改的文件 |
| `~/.claude/merit/merit_gate.py` | 源代码参考（结构索引 L12-44） |
| `~/.claude/merit/EVOLVE_README.md` | 自进化文档参考 |
| `~/.claude/merit/credit_manager.py` | 积分 CLI 参考 |
| `~/.claude/projects/-Users-allenbot/memory/CHANGELOG.md` | 变更日志 |
| `~/.claude/projects/-Users-allenbot/memory/backlog.md` | 遗留清单 |

## 验证标准

- [ ] 文档内容与 merit_gate.py 当前功能一一对应
- [ ] 文件清单与实际 `ls ~/.claude/merit/` 一致
- [ ] verify 跑 stone_guard_v7_design.md 无 ❌
- [ ] Sonnet code-review 无 Critical 问题
- [ ] CHANGELOG 已更新
- [ ] 自审五关全 ✅
