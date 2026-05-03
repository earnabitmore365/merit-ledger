---
name: qa-verify
description: "Know Your Cashflow 的增量验证和边界检查。在每完成一个模块后运行，验证实现是否符合架构设计。包括 5 条验证标准的逐条检查、边界门检查（组件不读DB/store不操作UI/服务层不进状态/不引入新依赖）。任何验证、测试、质量检查任务必须使用此技能。"
---

# QA Verify Skill — 增量验证 + 边界检查

## 验证流程

每完成一个模块后执行：

### 1. 语法检查
```bash
cd /Volumes/SSD-2TB/project/cashflowAPP
npx tsc --noEmit 2>&1 | head -30
```

### 2. 边界门检查
扫描文件内容，检查违规模式：

| 门 | 检查 | 违规标记 |
|----|------|---------|
| 组件不读 DB | grep -r "expo-sqlite" src/components/ | 发现 import 'expo-sqlite' |
| Store 不操作 UI | grep -r "react" src/stores/ | 发现 react import |
| 不引入新依赖 | 对比 package.json Phase 1 许可列表 | 出现额外包 |

### 3. 功能验证（5 条标准）

```
标准 1：记一笔 "加油80" → 解析为 -80 + ["加油"]
  检查 src/services/parser.ts 有对应逻辑

标准 2：自动匹配/手动选择 → keyword_rules 写入
  检查 src/services/tag-matcher.ts + db/queries.ts upsertKeywordRule

标准 3：再记 "加油50" → 自动匹配"交通"
  检查 tag-matcher 读取 keyword_rules 逻辑

标准 4：上滑/下滑确认 → 保存为收入/支出
  检查 SwipeBubble 手势 + record-store 保存

标准 5：查看历史 → 按日期分组显示
  检查 getRecordsByDate query + history.tsx 渲染
```

### 4. 跨模块一致性
- Data Agent 输出的类型定义与 UI Agent 使用的类型一致？
- Store 暴露的 action 签名与组件调用的签名匹配？
- db/queries 返回类型与 services 消费类型匹配？

## 输出格式
```
模块: [模块名]
  语法检查: PASS / FAIL
  边界门: PASS / FAIL (违规: ...)
  功能覆盖: N/5
  一致性问题: [如有]
  结论: PASS / FAIL (原因)
```
