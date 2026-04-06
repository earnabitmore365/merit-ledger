# Ralph Loop 修复同步到本地 lab/

## Context
Ralph loop 对 Vultr 部署版代码跑了 108 遍审查，修复了 5 个 bug（含 3 个实盘 P0）+ 大量死代码清理 + 代码质量改进。需要同步到本地 lab/ 并部署到 Vultr。

## 步骤
1. rsync Ralph 输出 → 本地 lab/（覆盖，不删除本地多出的文件）
2. 本地 lab/ 全量 py_compile 验证
3. 给老板 Vultr 部署命令

## 关键文件
- 来源：`/tmp/ralph_review/20260327-1311/lab/`（58 个 py 文件，已验证全通过）
- 目标：`/Volumes/BIWIN NV 7400 2TB/project/auto-trading/lab/`

## 验证
- py_compile 全量通过
- 5 个 bug 修复已由白纱验证正确（见本会话记录）
