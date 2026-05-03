---
description: 锻造 — 改代码的标准工作流：verify pre → 理解范围 → 实施 → 审查 → verify post → Opus 审查
---

# /forge — 锻造

> 铁律：**禁止猜想，一切以数据为准。**
> 所有结论必须来自实际运行结果或命令输出。

**红旗词自检（输出前扫一遍，出现就停）：**

| 词 | 类型 | 处理 |
|----|------|------|
| 显然 / 顺手 / 应该是要 / 理所当然 | 意图猜测 | 停下问执事，不自行处理 |
| 应该能跑 / 应该没问题 / 应该不会 | 技术猜测 | 停下跑命令验证 |
| 感觉 / 大概 / 估计 / 似乎 / 可能会影响 | 技术不确定 | 调黑丝讨论 |
| 不影响 / 暂时 / 先跳过 / 稍后 / 不重要 | 遗留信号 | 判断后处理（见下方规则） |

> Hook 会在每次工具调用前自动检测。发现红旗词 = 收到提醒时按上表处理。

**遗留信号的处理规则（不能只是"登记了事"）**：

| 情况 | 动作 |
|------|------|
| 立刻能修且不影响当前任务 | 直接修，不登记 |
| 小改动但会打断当前任务 | 登记 `backlog.md`，当前任务完成后立刻处理 |
| 大改动（多文件/有依赖）| 登记 `backlog.md`，单独开一轮 verify --pre → 改 → verify --post |
| P0（会导致报错/功能异常）| 不管当前任务，立刻处理 |

**backlog.md 登记格式**：
```
- [ ] [YYYY-MM-DD HH:MM] <内容>
      触发场景：正在做什么时发现
      处理时机：任务完成后立刻 / 需单独 verify / P0 立刻
      优先级：P0 / P1 / P2
```

登记后必须在当前任务摘要里注明"backlog 有 N 条待处理"，不能无声无息。

**verify 结果汇报规则**：
- ❌ 错误：必须逐条说明，立刻处理或登记 backlog
- ⚠️ 警告：同样必须逐条汇报，让老祖决定处理还是接受
- 禁止说"只有 ⚠️ 无 ❌ 可以继续"然后跳过——⚠️ 也要逐条交代清楚

---

## 开工前：建 Task Tracker（第一件事，不跳）

用 TaskCreate 工具为每个 Phase 建 task，建完再开始：

- Phase 0：verify --pre
- Phase 1：读文档 + 验证标准
- Phase 2.1：[第一个具体改动，如"改 feed_gateway.py 心跳逻辑"]
- Phase 2.2：[第二个具体改动]
- Phase 2.N：[……每个改动文件/功能独立一条]
- Phase 3：verify --post
- Phase 3.5：维护 verify
- Phase 4：Opus 审查
- Phase 4.5：git commit
- Phase 5：完成摘要 + 文档更新

**Phase 2 必须按实际改动点拆开，不能用一条"实施改动"包住全部。**
每个改动文件或功能单独一个 task，改完一个打勾一个。

每个 Phase 完成时用 TaskUpdate 改状态为 completed。
**未 completed 的 task = 没做完，不能跳。**

---

## Phase 0：开工前检查

```bash
# 自动检测当前项目的 verify 脚本（*-verify.py 命名规范）
VERIFY=$(find "$(python3 -c "
import os; p=os.getcwd()
for _ in range(6):
    if os.path.exists(os.path.join(p,'.wuji-root')): print(p); break
    p=os.path.dirname(p)
")" -maxdepth 1 -name "*-verify.py" 2>/dev/null | head -1)
[ -z "$VERIFY" ] && echo "❌ 未找到 *-verify.py，停止" && exit 1
echo "使用：$VERIFY"
python3 "$VERIFY" --pre
```

记录当前违规基线。有 ❌ 级违规先修，再进 Phase 1。

✅ 完成后：TaskUpdate Phase 0 → completed，再进 Phase 1。

---

## Phase 1：理解范围 + 制定验证标准

### 1. 列出涉及模块和技术

先列出这次任务涉及的所有模块和技术栈（如 DuckDB、SQLite、ZMQ、systemd 等）。

### 2. 查知识库 + 读文档（先于读代码）

**Step A — 先查知识库**

```bash
# 查与当前任务相关的规则和知识
grep -r "tags:.*trigger/写代码前" /Volumes/SSD-2TB/无极开天/wiki/ -l
# 或直接读全局索引
# Read /Volumes/SSD-2TB/无极开天/wiki/INDEX.md
```

有命中 → 读相关页面，把规则带入后续步骤。
查不到 → 记录在 `wiki/_incoming.md`（"查不到 X"），继续。

**Step B — 读项目文档**

**每个涉及模块，先找并读对应的 README / 文档，再看代码。**

- 项目模块 → 读对应目录的 `README.md`
- 外部技术（DuckDB / SQLite / ZMQ 等）→ 读项目内自建的技术文档（如 `文档/duckdb.md`）
- 找不到文档 → **先上网搜**，不靠记忆猜

**Step C — 文档空白时上网搜**

知识库和项目文档都没有答案时：

```
文档空白 → 上网搜同类问题和解法
         → 把搜索结果存入 wiki/raw/external/
         → 有数据后再决定方案（必要时才调 Opus）
```

禁止：文档空白 → 直接猜 → 调 Opus 再猜。每次猜测都是无效工作。

**不查库、不读文档、不搜网就动手 = 在猜，违反铁律。**

### 3. 读代码

文档读完后，再读相关源码文件，确认实际实现。

### 4. 判断是否调 Opus（改前分析）

满足以下任一条件 → 调 Opus，让 Opus 识别风险、边界条件、制定验证标准，再进下一步：

| # | 触发条件 |
|---|---------|
| 1 | 改动涉及状态机 / 流程控制的分支逻辑 |
| 2 | 改动涉及并发 / 异步 / 锁 / 队列 |
| 3 | 改动涉及金钱流（下单 / 仓位 / 风控阈值） |
| 4 | 改动的函数被 3 个以上调用方引用 |
| 5 | 发现任务范围内有方案没覆盖、但必须处理的新情况 |
| 6 | 预计修复跨 2 个以上文件 |

不满足 → 自己继续。

调 Opus 的 prompt：
```
你是影太极（或黑丝）。forge 要执行以下改动：[描述改动]。
涉及文件：[列出文件]。
请分析：边界条件有哪些？有什么陷阱？验证标准应该是什么？
不要自己动手，告诉我该怎么做。
```

### 3. 写下验证标准

改之前先写清楚每个改动的验证标准，**标准没写清楚不动手**：

```
改动 1：[描述]
  验证命令：[具体命令]
  预期输出：[预期结果]

改动 2：[描述]
  验证命令：[具体命令]
  预期输出：[预期结果]
```

✅ 完成后：TaskUpdate Phase 1 → completed，再进 Phase 2。

---

## Phase 2：实施改动

按改动逐一执行，**改一个验一个，不批量改完再统一验**。

每个改动完成后：

**Step A — 按 Phase 1 的验证标准执行验证**
跑验证命令，贴完整输出。输出与预期不符 → 修到符合为止。

**Step B — Agent 审查（安全+正确性）**

启动 1 个 Agent（subagent_type: Explore, model: sonnet），审查改动文件，三层检查：

**第一层：方案一致性**
- 方案要求的每个改动点是否都已实现？
- 有没有方案没提到的额外改动？

**第二层：正确性**
- 函数签名变更，调用方是否全部更新？（grep 确认）
- 边界值（空 / 零 / 负 / 超大）是否处理？
- 异常路径是否有处理？
- 数据类型传入传出是否匹配？

**第三层：安全性（交易系统）**
- 下单 / 仓位改动是否有数量上限、金额校验？
- 有没有硬编码 API key / secret？
- 新增外部调用是否有超时？

审查输出格式：
```
方案一致性：PASS / FAIL
正确性：PASS / FAIL
安全性：PASS / FAIL

问题清单：
- [直接修] xxx — 文件 A 第 N 行
- [调Opus] xxx — 文件 B 第 N 行
```

**Step C — 问题分流处理**

直接修（不调 Opus）：
- import 缺失 / 顺序错误
- 变量命名不一致
- 日志缺失
- 方案里已明确说明怎么做的

调 Opus 再修（满足上方 6 条任一）：
- 边界条件 / 并发竞态 / 安全漏洞
- 跨文件引用链改动
- 方案外的新决策

**Step D — py_compile 验证语法**
```bash
python3 -m py_compile <改动的文件>
```

✅ 每个子改动（Phase 2.x）完成后：TaskUpdate 该子 task → completed，再进下一个子改动或 Phase 3。

---

## Phase 3：verify --post

```bash
# $VERIFY 已在 Phase 0 定位，直接用
python3 "$VERIFY" --post
```

看原始结果，记录所有报警。

## Phase 3.5：维护 verify

对每条报警判断：

| 类型 | 处理 |
|------|------|
| 代码真问题 | 修代码 |
| verify 配置过时（假遗留） | **必须当场维护，不能标遗留** |

verify 过时 = 假遗留的情况：
- `CONSISTENCY_PAIRS` 里的函数不存在 → 删掉或更新
- 未注册 .py 文件 → 补进 `DIR_DOC_MAP`
- `ANTI_PATTERNS` 失效条目 → 删掉或更新

维护完 → 再跑 --post，直到全部 ✅。

✅ 完成后：TaskUpdate Phase 3 / Phase 3.5 → completed，再进 Phase 4。

---

## Phase 4：Opus 最终审查

调 Opus subagent：

```
你是影太极（或黑丝），审查刚才 forge 的改动：
1. 运行 git diff HEAD 查看实际改动
2. 逐项检查：
   - 有没有改变不该改的功能？
   - 有没有引入新 bug？
   - 有没有遗留 TODO/FIXME？
   - 每一行改动都能追溯到用户的要求吗？
3. 汇报 PASS 或 FAIL + 原因
```

PASS → 进 Phase 4.5。FAIL → 按意见修改后从 Phase 2 对应步骤重走。

✅ Opus PASS 后：TaskUpdate Phase 4 → completed，再进 Phase 4.5。

---

## Phase 4.5：git commit

Opus PASS 后 commit，不 push：

```bash
git add <改动的文件>
git commit -m "$(cat <<'EOF'
<根据改动内容写一句简洁的 commit message，说清楚改了什么>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

commit message 规则：
- 一句话说清楚改了什么（不超过 72 字符）
- 用动词开头（加 / 修 / 删 / 重构）
- 不写"应该""可能"，写实际改动

✅ commit 成功后：TaskUpdate Phase 4.5 → completed，再进 Phase 5。

---

## Phase 5：完成摘要 + 更新文档

### 回写知识库

完工后扫一遍：有没有值得沉淀的新知识？

判断标准（满足任一就写）：
- 踩了新坑、发现新规律
- 改变了架构决策或规则
- 发现知识库有偏差或缺漏

有 → append `wiki/_incoming.md`（格式见 `/Volumes/SSD-2TB/无极开天/wiki/_incoming.md` 模板）
     然后验证知识库完整性：
     ```bash
     python3 /Volumes/SSD-2TB/无极开天/wuji-verify.py
     ```
     （绝对路径，任何 cwd 都能跑）

无 → 在摘要里注明"无新知识沉淀"

### 更新 README（有则更新，无则新建）

如果这次改动涉及：
- 新学到的知识（踩坑、API 行为、性能特性）→ 更新对应技术文档
- 新增或修改了模块功能 → 更新模块的 README.md
- 发现文档记录有误 → 当场修正

**学到了就更新，不留到以后。**

### 完成摘要

```
🔨 锻造完成
   改了什么：[文件列表 + 改动说明]
   验证结果：[贴关键输出]
   文档更新：[更新了哪些文档，没有则写"无"]
   遗留清单：[诚实列出未完成的，没有则写"无"]
```

✅ 完成后：TaskUpdate Phase 5 → completed。任务结束。

---

## 规则

- 改一个验一个，不批量
- 验证标准改之前写，不是改完再想
- 禁止猜想，结论必须有命令输出支撑
- 涉及实盘改动，执事审查 PASS 后才能上
