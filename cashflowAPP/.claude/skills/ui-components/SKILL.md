---
name: ui-components
description: "Know Your Cashflow 的 React Native UI 组件。包括 SwipeBubble（上滑/下滑手势确认气泡）、AutoCompleteInput（带搜索建议的输入框）、TagPicker（标签选择/创建弹窗）、TagBadge（标签徽章）、RecordCard（记录卡片）、QuickInput（快速输入容器）。任何 UI 组件开发任务必须使用此技能。"
---

# UI Components Skill — Phase 1 组件

## 组件总览

### SwipeBubble.tsx
核心交互组件：用户输入解析后变气泡，上滑/下滑确认。

```
Props:
  amount: number              // 解析后的金额
  tokens: string[]            // 关键词
  matchedTags: Tag[]          // 自动匹配的标签
  unmatchedTokens: string[]   // 未匹配的词
  onConfirm: (direction: 'up' | 'down') => void
  onDismiss: () => void
  visible: boolean

手势：
  上滑 → 收入（金额变绿色正号）
  下滑 → 支出（金额变红色负号，默认）
  
视觉：
  背景半透明遮罩
  中央圆形气泡，显示金额（大号）+ 标签列表
  箭头指示：↑ 收入 / ↓ 支出
  向下重力动画（默认状态）
```

### AutoCompleteInput.tsx
文字输入框，输入时搜索历史记录。

```
Props:
  onParse: (text: string) => void     // 输入完成回调
  placeholder?: string

行为：
  - 输入时实时搜索最近的 keyword_rules 历史
  - 显示匹配建议列表
  - 回车/提交 → 调用 onParse
  - 空输入阻止提交
```

### TagPicker.tsx
弹窗选择或创建标签。

```
Props:
  visible: boolean
  unmatchedTokens: string[]      // 未匹配的关键词，作为创建建议
  existingTags: Tag[]             // 已有标签列表
  onSelect: (tagId: number) => void
  onCreate: (name: string) => void
  onDismiss: () => void

行为：
  - 搜索/过滤已有标签
  - 点击已有标签 → onSelect
  - 无匹配时显示"创建新标签 [关键词]" → onCreate
  - 支持标签颜色选择
```

### TagBadge.tsx
标签显示徽章。

```
Props:
  tag: Tag
  onRemove?: () => void        // 可关闭模式

视觉：
  圆角背景，颜色=tag.color
  左侧 icon（如果有）
  文本显示 tag.name
  右侧 × 按钮（onRemove 时显示）
```

### RecordCard.tsx
单条记录卡片，用于历史列表。

```
Props:
  record: Record & { tags: Tag[] }
  onPress?: () => void

视觉：
  左侧金额（红负/绿正）
  右侧标签列表（TagBadge 行）
  下方日期（相对时间："今天 14:30"/"昨天"/"5月1日"）
```

### QuickInput.tsx
组合容器，编排记账流程。

```
Props: 无（自包含）

内部状态：
  inputText: string
  parseResult: ParseResult | null
  matchResult: MatchResult | null
  showTagPicker: boolean
  currentDirection: 'up' | 'down'

流程：
  1. AutoCompleteInput 输入完成
  2. 调 parser.parseInput() 解析
  3. 调 tagMatcher.matchTags() 匹配
  4. 有匹配 → 显示 SwipeBubble
  5. 无匹配 → SwipeBubble + TagPicker
  6. 用户滑动确认 → 调 store.addRecord()
  7. 保存后重置状态
```

## 依赖
- react-native-gesture-handler (SwipeBubble)
- Zustand stores (QuickInput → record-store, tag-store)
- @expo/vector-icons (TagBadge icon)
