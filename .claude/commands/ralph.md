---
description: Ralph Loop — 循环审查修复 Loop/ 里的代码直到完美
---

按以下流程执行 Ralph Loop。自动循环不停，每轮一行汇报后直接进入下一轮。老板随时可以插话、改方向、喊停。

**准备阶段：**

1. 读 `/Volumes/BIWIN NV 7400 2TB/Loop/PROMPT.md` 了解审查规则（多遍扫描策略）
2. 检查 Loop/ 里有没有代码文件，没有就提醒老板先丢代码进去
3. 初始化 git（如果还没有）：`git init && git add -A && git commit -m "initial: 原始代码（loop 前）"`
4. 如果 PROGRESS.md 没有文件检查清单，初始化清单（列出所有 .py 文件为待扫描）
5. 在 Loop/ 里创建 `README.md` 骨架（审查时间、文件数、修复记录表头、文件状态全部"待扫描"）。commit。

**循环阶段（连续 5 轮无新发现自动收尾，老板也可随时喊停）：**

按 PROMPT.md 的多遍策略执行：
- 第 1 遍：P0（bug、crash）
- 第 2 遍：P1（死代码）
- 第 3 遍：P2（文档与代码不符）
- 第 4 遍：P3（跨文件一致性、风格）
- 第 5 遍+：精细化（犹豫过的现在都算问题）

每轮做一件事：
1. 检查 PROGRESS.md 的当前遍数和文件检查进度
2. 从未打勾的文件中找当前优先级的问题
3. 修复它（一轮只修一个问题或同文件同类问题）
4. 验证：`python3 -m py_compile <文件>`
5. 更新 PROGRESS.md（记录本轮、勾选文件）
6. 更新 README.md（修复记录表追加、文件状态更新）
7. `git add -A && git commit -m "loop N: 具体改了什么"`
8. 简要汇报：`🔄 第N轮 | 改了什么 | 下一轮方向`
9. 本遍所有文件扫完 → 推进到下一遍，重置文件清单

**自动收尾条件：** 连续 5 轮扫描未发现任何新问题（每轮汇报"无新发现"计 1 次，发现问题则重置计数）。达到 5 次后自动进入收尾流程。

**老板喊停 或 自动收尾时：**

1. 完善 README.md 最终版（补文件结构树、统计、git 查看命令）
2. `git add -A && git commit -m "loop: 收尾"`
3. 复制到 `/Volumes/BIWIN NV 7400 2TB/Loop Done/YYYYMMDD-HHMM/`
4. 清空 Loop/（只保留 ralph_loop.sh、run.sh、PROMPT.md、PROGRESS.md、CLAUDE.md）
5. 重置 PROGRESS.md
6. 汇报：总轮次、总遍数、修复摘要

**禁止事项：**
- 不改业务逻辑
- 不删整个文件
- 不加新功能
- 不重构架构
- 不自行写 STATUS: DONE
