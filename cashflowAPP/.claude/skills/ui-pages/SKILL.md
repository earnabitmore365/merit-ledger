---
name: ui-pages
description: "Know Your Cashflow 的 Expo Router 页面和导航。包括首页记账（index.tsx）、历史记录（history.tsx）、设置管理（settings.tsx）、导航布局（_layout.tsx）。任何页面开发或导航结构改动必须使用此技能。"
---

# UI Pages Skill — Phase 1 页面

## 路由结构

```
src/app/
├── _layout.tsx          # 根布局（Tab 导航）
└── (tabs)/
    ├── _layout.tsx      # Tab 布局
    ├── index.tsx        # 首页：记账
    ├── history.tsx      # 历史：按日期分组记录
    └── settings.tsx     # 设置：标签管理
```

## _layout.tsx（根布局）
- Expo Router Stack 导航
- 标题："Know Your Cashflow"

## (tabs)/_layout.tsx（Tab 布局）
- 4 个 Tab：首页/记录/统计（Phase 2）/设置
- Phase 1 统计 tab 占位（显示"即将推出"）

## (tabs)/index.tsx（首页）
```
使用 QuickInput 组件
├── 顶部：今日日期 + 余额摘要
├── 中间：QuickInput（主要交互区）
└── 底部：今日快速统计（支出/收入/笔数）

数据流：
  QuickInput 完成记账 → 自动刷新今日摘要
  页面加载时 fetchRecords('today')
```

## (tabs)/history.tsx（历史）
```
FlatList 按日期分组

数据结构：[{ date: string, records: RecordCard[] }]

├── SectionHeader: "今天" / "昨天" / "5月1日 周四"
├── RecordCard × N
└── 底部：本月汇总（总支出/总收入）

交互：
  点击 RecordCard → Phase 2 跳转编辑
  左滑删除（Phase 2）
```

## (tabs)/settings.tsx（设置）
```
标签管理为主

├── 标签列表（所有 TagBadge）
├── 创建标签按钮
├── TagPicker 弹窗
└── 数据管理
    ├── 清除所有数据（确认弹窗）
    └── 导出 CSV（Phase 2）

交互：
  点击标签 → 编辑颜色/名称
  长按标签 → 删除确认
  创建 → 调 tagStore.createTag()
```

## 依赖
- QuickInput 组件（首页）
- RecordCard 组件（历史页）
- TagBadge + TagPicker（设置页）
- record-store + tag-store（全部页面）
