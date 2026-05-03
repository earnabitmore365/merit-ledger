---
name: services
description: "Know Your Cashflow 的服务层和状态管理。chinese-amount-parser（中文金额转数字）、parser（自然语言输入解析）、tag-matcher（关键词标签自动匹配引擎）、Zustand stores（record-store + tag-store）。任何输入解析、标签匹配、状态管理的任务必须使用此技能。"
---

# Services Skill — 服务层 + 状态管理

## 类型定义

```typescript
interface ParseResult {
  amount: number;   // 负=支出，正=收入
  tokens: string[]; // 剩余文本分词
  raw: string;      // 原始输入
}

interface MatchResult {
  matched: Tag[];
  unmatched: string[];
  confidence: number; // 0-1
}

interface Tag {
  id: number;
  name: string;
  color: string;
  icon?: string;
}
```

## chinese-amount-parser.ts

纯函数，从字符串中提取中文金额。

| 输入 | 输出 |
|------|------|
| "三块五" | 3.5 |
| "五十刀" | 50 |
| "一块五毛" | 1.5 |
| "十五块" | 15 |
| "两块钱" | 2 |
| "无金额" | null |

规则：
- 块/块钱 = 元
- 毛/毫 = 角 (0.1)
- 分 = 分 (0.01)
- 刀 = AUD（数字部分照常提取）
- "两" = 2
- "十"/"拾" = 10
- "百"/"佰" = 100
- 支持组合："三百二十块五毛" = 320.5

导出函数：`extractChineseAmount(text: string): number | null`

## parser.ts

从用户输入解析金额和关键词。

| 输入 | ParseResult |
|------|-------------|
| "加油80" | { amount: -80, tokens: ["加油"], raw: "加油80" } |
| "工资5000" | { amount: 5000, tokens: ["工资"], raw: "工资5000" } |
| "三块五 可乐" | { amount: -3.5, tokens: ["可乐"], raw: "三块五 可乐" } |
| "收入200 in" | { amount: 200, tokens: ["收入"], raw: "收入200 in" } |
| "花了五十块吃饭" | { amount: -50, tokens: ["吃饭"], raw: "花了五十块吃饭" } |

规则：
1. 先尝试 chinese-amount-parser 解析中文金额
2. 再尝试正则提取阿拉伯数字（默认取最后出现的数字）
3. 去掉数字/金额部分，剩余文本按空格/逗号分词 → tokens
4. 金额默认负值（支出）
5. 文本含 "in"/"收入" 结尾 → 正值（收入）
6. 纯数字无文本 → tokens 为空数组
7. 全文无数字 → amount: 0, tokens: 全部分词

导出函数：`parseInput(text: string): ParseResult`

## tag-matcher.ts

将 tokens 匹配到已有标签。

规则：
1. 对每个 token 查 keyword_rules 表
2. 按 hit_count 降序排列（常用优先）
3. 多个 token 匹配不同标签时，全部返回
4. 匹配度 = 匹配的 token 数 / 总 token 数
5. 无匹配 → { matched: [], unmatched: allTokens, confidence: 0 }

导出函数：`async matchTags(tokens: string[]): Promise<MatchResult>`

## record-store.ts (Zustand)

```typescript
interface RecordStore {
  records: Record[];
  loading: boolean;
  error: string | null;
  addRecord(amount: number, tagIds?: number[]): Promise<void>;
  deleteRecord(id: number): Promise<void>;
  updateTags(recordId: number, tagIds: number[]): Promise<void>;
  fetchRecords(range?: { start: string; end: string }): Promise<void>;
  fetchRecordsByDate(): Promise<{ date: string; records: Record[] }[]>;
}
```

## tag-store.ts (Zustand)

```typescript
interface TagStore {
  tags: Tag[];
  recentTags: Tag[];
  loading: boolean;
  createTag(name: string, color?: string, icon?: string): Promise<Tag>;
  deleteTag(id: number): Promise<void>;
  getAllTags(): Promise<void>;
  getRecentTags(limit?: number): Promise<Tag[]>;
}
```
