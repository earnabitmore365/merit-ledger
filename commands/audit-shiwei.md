---
name: audit-shiwei
description: 太极审计石卫 — 读石卫操作日志，按三准则+第一性原理逐条评判，给石卫打分，审批子rule提案。
user-invocable: true
---

# 太极审计石卫

## 执行步骤

1. **找未审计的日志**：比对 `~/.claude/merit/shiwei_log/` 和 `~/.claude/merit/shiwei_audit/` 的日期，找出有日志但没审计报告的天数

2. **逐条评判**（按当天 shiwei_log 的每条记录）：
   - **完整性**：该拦的都拦了吗？有漏网的吗？
   - **真实性**：拦对了吗？AI 评分准不准？MiniMax 原始返回合理吗？
   - **有效性**：拦截后 AI 改正了吗？评分有没有影响行为？
   - **第一性原理**：规则本身合理吗？有冗余可合并的吗？

3. **给石卫打分**：
   ```bash
   python3 ~/.claude/merit/credit_manager.py shiwei add <分数> "审计原因"
   python3 ~/.claude/merit/credit_manager.py shiwei sub <分数> "审计原因"
   ```
   - 全部正确 → +5
   - 有误拦 → 每次 -3
   - 有漏拦（该拦没拦，需交叉比对 daily md）→ 每次 -5
   - 规则建议被采纳 → +3

4. **审批子 rule 提案**：读 `~/.claude/merit/rule_proposals.json` 里 status=pending 的条目，逐条判断批准/拒绝/修改

5. **输出审计报告**：写入 `~/.claude/merit/shiwei_audit/YYYY-MM-DD.md`，格式：
   ```
   # 石卫审计报告 YYYY-MM-DD
   **审计者**: 太极宗主
   **审计范围**: YYYY-MM-DD 全天操作日志

   ## 统计
   | 指标 | 数值 |
   |------|------|
   | 总操作数 | N |
   | 拦截（DENY） | N |
   | 评分（SCORE） | N |
   | 误拦 | N |
   | 漏拦 | N |

   ## 审计结论
   - ✅/❌ 完整性：...
   - ✅/❌ 真实性：...
   - ✅/❌ 有效性：...
   - ✅/❌ 第一性原理：...

   ## 分数变动
   +N / -N = 总计 ±N
   石卫：X → Y 分（段位）

   ## 已审批提案
   | # | 提案 | 决定 |
   |---|------|------|
   ```

6. **更新 shiwei_credit.json 的 audit_streak**：连续审计天数 +1
