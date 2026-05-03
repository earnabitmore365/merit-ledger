# Claude Code 自定义配置备份

## 内容

### 全局配置
| 文件 | 说明 |
|------|------|
| `.claude/settings.json` | DeepSeek API、hooks、权限、插件、MCP 配置 |
| `.claude/CLAUDE.md` | 无极堂规 — 全局指令 |

### 自定义 Commands
| 命令 | 说明 |
|------|------|
| `commands/decree.md` | 圣旨 — 任务路由 |
| `commands/forge.md` | 锻造 — 新建代码 |
| `commands/reforge.md` | 重锻 — 修复/审查/重构 |
| `commands/wiki.md` | 认知 — 调研/文档/知识库 |
| `commands/audit-shiwei.md` | 执事审计 |
| `commands/letterfromtaiji.md` | 太极来信 |
| `commands/ralph.md` | Ralph |
| `commands/reward.md` | 奖励 |
| `commands/code-simplifier.md` | 代码简化 |
| `commands/claude.md` | Claude |

### 自定义 Skills
| Skill | 说明 |
|-------|------|
| `skills/pine/` | Pine Script v6 代码生成 |
| `skills/mcp-hub/` | MCP 中枢 |
| `skills/reflect/` | 反思学习 |
| `skills/monitor-command/` | 远程监控脚本生成 |
| `skills/test-runner/` | 自动化测试执行 |
| `skills/todo-manager/` | TODO 扫描 |
| `skills/skill-validator/` | Skill 结构校验 |
| `skills/prompt-budget-analyzer/` | GEP Prompt 预算分析 |
| `skills/time-checker/` | 时间检查 |
| `skills/hook-health/` | Hook 健康检查 |
| `skills/gh-fix-ci/` | GitHub CI 修复 |
| `skills/github/` | GitHub 操作 |
| `skills/qmd/` | QMD |
| `skills/Agent Development/` | Agent 开发指南 |
| `skills/evo-*/` | 进化引擎相关（cycle-guard, digest, gene-recommender, lint, narrative-compactor, trend-tracker, scorecard, crossover） |
| `skills/agent-browser/` | 浏览器自动化 |
| `skills/chrome-devtools/` | Chrome DevTools |
| `skills/connect-apps/` | 应用连接 |
| `skills/deployment-engineer/` | 部署工程 |
| `skills/webapp-testing/` | Web 测试 |
| `skills/code-stats/` | 代码统计 |

### MCP 服务器
| MCP | 说明 |
|-----|------|
| `mcp/wuji_ops.py` | 交易系统运维（Vultr 服务器管理） |
| `mcp/pine-mcp/server.py` | Pine Script 代码生成 |
| `session-query/index.ts` | 对话种子查询（查看 agent 的 daily 会话记录） |
| `github-sync/index.ts` | GitHub 同步（本地 ↔ 远程 repo 差异比对和推送） |

### 太极↔两仪通道
| 文件 | 说明 |
|------|------|
| `channel-server/webhook.ts` | 通道 Webhook 服务 |
| `channel-server/package.json` | |

### 自定义 Scripts (hooks)
| 脚本 | 说明 |
|------|------|
| `scripts/session_start.py` | 会话启动 |
| `scripts/db_write.py` | 数据库写入 |
| `scripts/gate.py` | PreToolUse 门控 |
| `scripts/pre_compact_save.py` | 压缩前保存 |
| `scripts/second_brain_sync.py` | 第二大脑同步 |
| `scripts/archive_daily.py` | 每日归档 |
| ... + 其他 19 个脚本 |

### 插件配置
| 文件 | 说明 |
|------|------|
| `plugins/installed_plugins.json` | 已安装插件列表（claude-hud, taiji-audit, engineering, harness） |

### cashflowAPP 项目
| 目录 | 说明 |
|------|------|
| `cashflowAPP/.claude/agents/` | data-agent, ui-agent, qa-agent |
| `cashflowAPP/.claude/skills/` | database, services, ui-components, ui-pages, qa-verify, orchestrator |

## 使用

重装 Claude Code 后，将对应文件拷回 `~/.claude/` 即可恢复。
