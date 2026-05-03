---
name: pine
description: Pine Script v6 生成 — 调 MCP 工具强制分步执行，不跳步
---

# /pine — Pine Script 生成（MCP 版）

**用法**：`/pine <策略名>` 或直接交给白纱做

**MCP server 名：`pine-mcp`（调工具时用 `pine-mcp` 查找）**

---

## 架构

```
代码来源不限（老祖给 / 进化树出 / 自己研究 / 模板生成 — 都可以）
    │
    ├─ Step 0：确认策略参数
    │
    ├─ Step 1：pine_read_docs  ← 搜知识库 → 逐条确认规则
    │   └─ 对不上的 → 上网搜 → 存 wiki → 回来
    │
    ├─ Step 2：pine_render     ← 可选，有模板就用，没有就自己写
    │
    ├─ Step 3：pine_validate   ← 格式验证（必须过）
    │   └─ pass 才能写文件
    │
    ├─ Step 4：pine_write      ← 写入 Downloads/
    │   └─ 读回确认
    │
    └─ Step 5：告知老祖
```

**分步状态锁（check_code 机制）**：
- 每步 MCP 工具返回一个 `_check_code`，下一步必须传入此码
- 不调上一步 → 拿不到 code → 无法调下一步（一次性打包跑会被中断）
- 流程：`read_docs → render（可选）→ validate → write`
- 手写代码不调 render → `read_docs → validate → write`
- 一轮写完后可重新调 `read_docs` 开始下一轮

---

## 开工前：建 Task Tracker

用 TaskCreate 工具建 task，建完再开始：

- Step 0：确认策略参数
- Step 1：pine_read_docs（MCP）+ 逐条确认
- Step 2：pine_render（MCP）
- Step 3：pine_validate（MCP）
- Step 4：pine_write（MCP）
- Step 5：告知老祖

每个 Step 完成时用 TaskUpdate 改状态为 completed。
**未 completed 的 Step = 没做完，不能跳。**

---

## Step 0：确认策略参数

策略参数来自老祖或进化树。确认清楚再进 Step 1：

| 问题 | 示例 |
|------|------|
| 策略名 | `rsi_reversal` |
| 指标类型 | supertrend / macd / rsi / ema_cross（详见 `知识库/两仪/自动交易系统/回测/策略/`）|
| 参数值 | `{"rsi_period": 5, "oversold": 15, "overbought": 85}` |
| 开单策略类型 | pure / ttp_close / ttp_highlow（可选） |

> 参数不明确 → 停下问老祖，不猜。

✅ 完成后：TaskUpdate → completed，再进 Step 1。

---

## Step 1：pine_read_docs（MCP 强制步）

调 MCP server `pine-mcp` 的 `pine_read_docs` 工具。会到 Obsidian 知识库搜索 Pine Script 相关文档，返回规则摘要。

### 收到结果后，必须逐条确认：

```
规则 1：「……」（文档 A）
  → 对应当前策略：______

规则 2：「……」（文档 B）
  → 对应当前策略：______

……
```

### 规则确认不了的流程：

```
规则讲不清楚 / 找不到对应位置
    ↓
上网搜 Pine Script 官方文档 / 可靠来源
    ↓ 找到答案
用 /wiki 存入知识库
    ↓
回到 Step 1 继续确认
    ↓
上网也查不到
    ↓
停下问老祖（不猜）
```

> **核心**：数据驱动，不是直觉驱动。不知道就找数据，找到存 wiki。

✅ 全部确认完成后：TaskUpdate → completed，再进 Step 2。

---

## Step 2：pine_render（MCP 强制步）

调 MCP server `pine-mcp` 的 `pine_render` 工具。

**传参**：
- `output_type`: `"indicator"` 或 `"strategy"`
- `indicator_type`: `"supertrend"` / `"macd"` / `"rsi"` / `"ema_cross"`
- `strategy_type`: `"pure"` / `"ttp_close"` / `"ttp_highlow"`
- `params`: 从 Step 0 拿到的参数 dict

**检查结果**：
- ✅ 代码非空，含 `//@version=6`
- ✅ 参数值正确（如 `rsiPeriod  = input.int(5, ...)`）
- ❌ 代码空或不完整 → 重试

> 如果要做 indicator + strategy 两个文件：调两次 `pine_render`。

✅ 完成后：TaskUpdate → completed，再进 Step 3。

---

## Step 3：pine_validate（MCP 强制步）

调 MCP server `pine-mcp` 的 `pine_validate`，传入 Step 2 生成的代码。

**检查项**：
- `//@version=6` 声明
- 无 markdown 代码围栏
- indicator/strategy 头部正确
- strategy() 单行
- indicator 有 plot 输出
- 未使用 `when=` 参数

**结果处理**：
- ✅ `pass: true` → 进 Step 4
- ❌ `pass: false` → 按 issues 修，重跑 render → 再 validate
- ⚠️ warnings 无 error → 逐条说明给老祖听

✅ 完成后：TaskUpdate → completed，再进 Step 4。

---

## Step 4：pine_write（MCP 强制步）

调 MCP server `pine-mcp` 的 `pine_write`，传入 Step 3 验证通过的代码和文件名。

**文件命名**：
- 信号 indicator：`<策略名>_signal.md`
- 纯信号 strategy：`<策略名>_pure.md`
- TTP close：`<策略名>_ttp_close.md`
- TTP highlow：`<策略名>_ttp_highlow.md`

**检查结果**：
- ✅ `path` 是 `~/Downloads/` 下
- ✅ `size` > 0
- ✅ **必须 Read 读回文件确认内容正确**

✅ 完成后：TaskUpdate → completed，再进 Step 5。

---

## Step 5：告知老祖

输出格式：
```
✅ Pine Script 文件已生成
   信号 indicator：Downloads/<策略名>_signal.md
   开单 strategy： Downloads/<策略名>_<类型>.md

   使用方法：
   1. TradingView 先加信号 indicator
   2. 再加开单 strategy，Inputs 里选 Signal Source 为对应 indicator
   3. 运行回测

   参数：<列主要参数和默认值>
   信号逻辑：<一句话描述>
```

✅ 完成后：TaskUpdate → completed。全部任务结束。

---

## 违规红线

- **禁止**跳步（不调 read_docs → 规则没确认就开工）
- **禁止**改参数默认值
- **禁止**输出文件有代码围栏
- **禁止** strategy() 跨行
- **禁止**用"看起来对"替代实际检查
- **禁止**规则讲不清楚时不查数据直接猜 → 先上网搜，找不到再问老祖
- **加新模板必须同步写知识库**——改 `INDICATOR_TEMPLATES` 的同时，必须到 `知识库/两仪/自动交易系统/回测/策略/` 下建对应的 `.md` 条目，含参数表、信号逻辑、完整代码
