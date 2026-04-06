# 石卫路径匹配 bug 修复

## 问题
mission submit 用相对路径，实际 Write/Edit 用绝对路径，os.path.abspath 基于 hook cwd 展开导致不匹配。mission complete 报未完成。

## 根因
is_planned_action + mark_mission_item_done 用 `os.path.abspath` 展开相对路径，但 hook 运行的 cwd 跟两仪工作目录不同。

## 修复
1. is_planned_action：精确匹配失败时 fallback basename 匹配
2. mark_mission_item_done：同上
3. 白纱积分复核：补回 3 分押金 + 解锁 5 分

## 涉及文件
- `~/.claude/merit/merit_gate.py`（is_planned_action + mark_mission_item_done）
- `~/.claude/merit/credit.json`（积分补回）
