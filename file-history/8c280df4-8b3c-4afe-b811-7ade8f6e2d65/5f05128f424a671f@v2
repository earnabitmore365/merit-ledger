---
name: reward
description: 执事直接奖惩 — 给两仪加减分并记录原因。用法：/reward -80 原因 或 /reward +20 原因
user-invocable: true
---

# 执事奖惩令

执事（老板）直接输入的奖惩指令，石卫无条件执行。

## 解析参数

用户输入格式：`/reward <分数> <原因>`

例如：
- `/reward -80 没有按照老祖的准则来干活`
- `/reward +20 主动发现问题并完整修复`

## 执行步骤

1. 从参数中解析分数（正数或负数）和原因
2. 用 Bash 执行：
   ```
   python3 ~/.claude/merit/credit_manager.py add <agent_name> <分数> "执事奖惩：<原因>"
   ```
   - agent_name：读 credit.json 找当前项目对应的 agent（项目级 = 两仪）
3. 读取 credit.json 确认分数已变更
4. 输出结果：
   ```
   ⚖️ 执事奖惩令
   对象：<agent_name>
   变动：<分数>
   原因：<原因>
   当前积分：<新积分>
   ```

## 注意

- 执事的奖惩令不经过 AI 评分，直接写入 credit.json
- 正数 = 奖励，负数 = 惩罚
- 原因会记录在 credit.json 的 history 里，永久保留
- 如果没有指定分数或原因，提醒执事补全
