# 无极堂·天衡册

AI 行为管控闭环系统——规则→执行→反馈→学习→自进化。

## 核心组件

| 文件 | 作用 |
|------|------|
| `merit_gate.py` | 统一引擎，处理所有 Claude Code hook 事件 |
| `credit_manager.py` | CLI 工具（积分查询/加减/mission/申报/搜索） |
| `evolve.py` | 自进化引擎（cron 每15分钟，教训→规则→二次审查→写入） |
| `verify.py` | 四件套质检（语法+逻辑+全链路+文档） |
| `self_audit_core.md` | 自审协议·通用篇（规划期+收尾期六关） |
| `self_audit_taiji.md` | 自审协议·太极专属 |
| `self_audit_liangyi.md` | 自审协议·两仪专属 |
| `shiwei_captain.py` | 石卫队长（MiniMax 合同审查官） |

## 系统设计

- **10000 分制**：积分驱动等级（9级：凡体→大乘），等级决定权限
- **三律三法**：完整·真实·有效 + 知常·静制动·远谋
- **石卫**：PreToolUse 拦截破坏性操作，PostToolUse 验证信号
- **合同积分制**：签约（队长估分）→ 执行 → 验收（队长定 completion_rate）→ 发放
- **行为积分只扣不加**：正向积分从合同来，或老祖手动 /reward
- **自进化**：LEARNINGS 教训池 → evolve 聚类生成规则 → 二次审查 → 自动写入 rules.md
- **fcntl.flock**：所有积分写入加文件锁防并发

## 扣分表（只扣不加）

```
  fake_or_cheat:        -50
  same_error_3rd_time:  -38
  bypass_without_report: -25
  panic_no_analysis:    -13
  say_maybe_no_check:    -8
  flattery_filler:       -8
  ask_boss_tech:         -5
```

## 依赖

- Claude Code hooks 系统
- MiniMax M2.7-highspeed（语气识别+规则生成+二次审查）
- Python 3.12+

## 许可

私有项目，仅供内部使用。
