---
name: database
description: "Know Your Cashflow 的 SQLite 数据库层。包括 schema 定义、migration 脚本、CRUD 查询。涉及 records/tags/record_tags/keyword_rules 四张表的建表和操作。任何数据库相关的任务（建表、改 schema、写 query、迁移）必须使用此技能。"
---

# Database Skill — SQLite 数据层

## 数据模型（4 表）

```sql
CREATE TABLE records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  amount REAL NOT NULL,              -- 正=收入，负=支出
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  color TEXT DEFAULT '#666',
  icon TEXT,                         -- emoji 可选
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE record_tags (
  record_id INTEGER REFERENCES records(id) ON DELETE CASCADE,
  tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (record_id, tag_id)
);

CREATE TABLE keyword_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword TEXT NOT NULL,
  tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
  hit_count INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(keyword, tag_id)
);

CREATE INDEX idx_records_date ON records(created_at);
CREATE INDEX idx_keyword_rules_keyword ON keyword_rules(keyword);
```

## schema.ts 要求
- 导出 `getSchema()` → 返回包含所有 CREATE TABLE/INDEX 的 SQL 字符串
- 导出 `getDropAllSQL()` → DROP TABLE IF EXISTS 语句（用于测试重置）

## migrations.ts 要求
- 用 `expo-sqlite` 的 `openDatabaseAsync` 或 `SQLiteProvider`
- 初始迁移：建 4 表 + 索引
- 后续迁移：版本号递增，每个版本一个变更函数

## queries.ts CRUD 要求

### records
- `createRecord(amount: number): Promise<number>` — 返回 id
- `getRecord(id: number): Promise<Record | null>`
- `getRecordsInRange(start: string, end: string): Promise<Record[]>`
- `getRecordsByDate(): Promise<{date: string, records: Record[]}[]>` — 按日期分组
- `deleteRecord(id: number): Promise<void>` — CASCADE 自动删关联标签

### tags
- `createTag(name: string, color?: string, icon?: string): Promise<number>`
- `getAllTags(): Promise<Tag[]>`
- `getTag(id: number): Promise<Tag | null>`
- `deleteTag(id: number): Promise<void>` — CASCADE 删除关联

### record_tags
- `addTagToRecord(recordId: number, tagId: number): Promise<void>`
- `removeTagFromRecord(recordId: number, tagId: number): Promise<void>`
- `getTagsForRecord(recordId: number): Promise<Tag[]>`

### keyword_rules
- `upsertKeywordRule(keyword: string, tagId: number): Promise<void>` — 存在则 hit_count+1
- `getMatchingRules(keyword: string): Promise<{tag: Tag, hitCount: number}[]>`
- `deleteKeywordRule(id: number): Promise<void>`

## 验证方法
```typescript
// 验证建表
import * as SQLite from 'expo-sqlite';
const db = await SQLite.openDatabaseAsync(':memory:');
await db.execAsync(getSchema());
// 验证表存在
const tables = await db.getAllAsync("SELECT name FROM sqlite_master WHERE type='table'");
console.assert(tables.length === 4);

// 验证 CRUD
const id = await createRecord(-80);
const r = await getRecord(id);
console.assert(r.amount === -80);
