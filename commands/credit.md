---
name: credit
description: 查看信用积分、等级和排行榜。输入 /credit 查看当前状态，/credit history 查看变更记录。
user_invocable: true
---

# /credit — 信用积分查询

用 Bash 工具执行以下命令查看积分状态：

```bash
python3 ~/.claude/scripts/credit_manager.py show
```

如果用户附加了参数（如 `/credit history 黑丝`），执行：

```bash
python3 ~/.claude/scripts/credit_manager.py history <角色名>
```

将结果完整输出给用户。如果 credit_manager.py 不存在，告诉用户 Haiku Gate 未安装。
