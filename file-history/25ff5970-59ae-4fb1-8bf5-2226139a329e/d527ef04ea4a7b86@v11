# SSH 豁免 + test_memory.py

## Context

两个中优先级待做项。SSH 豁免影响两仪在 Vultr 操作（kill/重定向被误拦）。test_memory.py 让 verify.py 记忆系统的逻辑验证从 ⏳ 变 ✅。

---

## 1. SSH 豁免

**问题**：`check_bash_destructive` 对整个命令字符串做正则匹配。`ssh host "kill PID"` 里的 `kill` 被 DANGEROUS_COMMANDS 拦截，但远程操作不影响本地系统。

**方案**：在 `check_bash_destructive` 开头加 SSH 检测——命令以 `ssh ` 开头时跳过破坏性检查。

```python
# SSH 命令在远程执行，不影响本地系统
if cmd.strip().startswith("ssh ") or cmd.strip().startswith("scp "):
    return None
```

**为什么最简方案就够**：
- 石卫保护的是本地系统。远程服务器由远程管理员负责
- scp 也跳过——上传文件到远程不是本地破坏
- 如果以后需要审计远程操作，加到 shiwei_log 记录即可，但不拦截

**改动**：`~/.claude/merit/merit_gate.py` check_bash_destructive 函数加 2 行

---

## 2. test_memory.py

**测试项**（覆盖记忆系统四个脚本的核心功能）：

| # | 测试 | 检查什么 |
|---|------|---------|
| 1 | db_write TAIJI_PROJECT 常量 | = '-Users-allenbot' |
| 2 | db_write SKIP_DIRS 不含太极 | '-Users-allenbot' not in SKIP_DIRS |
| 3 | db_write ensure_schema 建表 | 临时 DB 有 messages + stop_points 表 |
| 4 | db_write remap_speaker_taiji | 白纱→太极, 黑丝→影太极 |
| 5 | db_write get_tags 标签匹配 | '回测' 命中 '技术验证' |
| 6 | session_start _get_level 导入 | 从 merit_gate 拿到正确结果 |
| 7 | session_start inject_rules 不崩 | 调用不报错 |
| 8 | daily_digest basic_tags | 关键词匹配返回标签 |
| 9 | daily_digest run_evolve 可调用 | 函数存在且可调 |
| 10 | pre_compact extract_text_from_content | 字符串和列表格式都能解析 |

**新增文件**：`~/.claude/scripts/test_memory.py`
**注册**：verify_registry.json memory.test_script 从 null 改为路径

---

## 改动文件

| 文件 | 改动 |
|------|------|
| `~/.claude/merit/merit_gate.py` | check_bash_destructive 加 SSH 豁免 |
| `~/.claude/scripts/test_memory.py` | 新建（10 项测试） |
| `~/.claude/merit/verify_registry.json` | memory.test_script 注册 |

## 验证

- `ssh host "kill 123"` 不被拦截
- `rm local_file` 仍被拦截（本地保护不变）
- `python3 test_memory.py` → 10/10 通过
- `python3 verify.py db_write.py` → 逻辑从 ⏳ 变 ✅
