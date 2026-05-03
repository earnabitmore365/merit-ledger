---
description: 回炉再造 — verify pre → 4 agent 并行审查 → 美容 → Opus 审查 → verify post
---

# /reforge — 回炉再造

> 铁律：**禁止猜想，一切以数据为准。**
> 所有结论必须来自实际运行结果或命令输出。

**红旗词自检（输出前扫一遍，出现就停）：**

| 词 | 类型 | 处理 |
|----|------|------|
| 显然 / 顺手 / 应该是要 / 理所当然 | 意图猜测 | 停下问执事，不自行处理 |
| 应该能跑 / 应该没问题 / 应该不会 | 技术猜测 | 停下跑命令验证 |
| 感觉 / 大概 / 估计 / 似乎 / 可能会影响 | 技术不确定 | 调黑丝讨论 |
| 不影响 / 暂时 / 先跳过 / 稍后 / 不重要 | 遗留信号 | 立刻 TaskCreate 登记 |

> Hook 会在每次工具调用前自动检测。发现红旗词 = 收到提醒时按上表处理。

---

## 开工前：建 Task Tracker（第一件事，不跳）

用 TaskCreate 工具为每个 Phase 建 task，建完再开始：

- Phase 0：verify --pre
- Phase 0.5：读文档
- Phase 1.1：[第一个审查修复项，如"修 feed_gateway.py 死代码"]
- Phase 1.2：[第二个审查修复项]
- Phase 1.N：[……每个修复点独立一条]
- Phase 2：美容
- Phase 3：Opus 审查
- Phase 4：verify --post + 维护 verify
- Phase 4.5：git commit
- 完成：摘要 + 文档更新

**Phase 1 审查修复必须按实际问题拆开，不能用一条包住全部。**

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

- 记录当前反模式违规基线
- 有 ❌ 级违规先修，再进 Phase 1

✅ 完成后：TaskUpdate Phase 0 → completed，再进 Phase 0.5。

## Phase 0.5：查知识库 + 读文档（审查前必做）

**Step A — 先查知识库**

```bash
grep -r "tags:.*trigger/写代码前" /Volumes/SSD-2TB/无极开天/wiki/ -l
```

有命中 → 读相关页面，把规则带入审查判断。
查不到 → 记录在 `wiki/_incoming.md`，继续。

**Step B — 读项目文档**

列出审查范围涉及的所有模块和技术栈，先读对应文档再开始审查：

- 项目模块 → 读对应目录的 `README.md`
- 外部技术（DuckDB / SQLite / ZMQ 等）→ 读项目内自建的技术文档
- 找不到文档 → **先上网搜**，不靠记忆猜

**Step C — 文档空白时上网搜**

```
文档空白 → 上网搜 → 把结果存入 wiki/raw/external/ → 再决定
```

禁止：文档空白 → 猜 → 调 Opus 再猜。

**不查库、不读文档、不搜网就动手 = 在猜，违反铁律。**

✅ 完成后：TaskUpdate Phase 0.5 → completed，再进 Phase 1。

---

## Phase 1：审查修复（自动循环）

### 准备

1. 确定审查范围：
   - 如果指定了模块路径（如 src/core/）→ 扫该目录下所有 .py
   - 如果指定了文件列表 → 用指定的
   - 如果都没指定 → 扫整个项目所有 .py
   - **禁止自行缩小范围**。给了模块就全扫，不能挑几个文件宣布 CLEAN

### 执行

并行启动 4 个 Agent（subagent_type: Explore, model: sonnet），每个负责不同维度：

**Agent 1 — 复用检查：**
- 重复代码（5+ 行相同的块）
- 可共享的函数（多处内联同一逻辑）
- 重复常量定义

**Agent 2 — 质量检查：**
- 死代码（未使用变量/不可达分支/废弃 import）
- 命名不清（变量/函数名不描述用途）
- 冗余状态（可推导的缓存值）
- 不必要的注释（描述显而易见的代码）

**Agent 3 — 效率检查：**
- 热路径重复 I/O（同一文件多次读取）
- N+1 模式
- TOCTOU 反模式（先检查存在再操作）
- 资源泄漏（未关闭的文件/连接）

**Agent 4 — 安全+正确性检查：**
- SQL/Shell/路径注入
- 并发竞态（无锁写入共享文件）
- 边界条件（None/空/溢出/off-by-one）

### 循环

4 个 agent 全部返回后，按问题类型分流处理：

**直接修（不调 Opus）：**
- 死代码、废弃 import、重复代码
- 命名改善、结构扁平化、helper 提取
- 不必要的注释

**必须先调 Opus 讨论方案，再动手修（满足以下任一条）：**

| # | 触发条件 |
|---|---------|
| 1 | 改动涉及状态机 / 流程控制的分支逻辑 |
| 2 | 改动涉及并发 / 异步 / 锁 / 队列 |
| 3 | 改动涉及金钱流（下单 / 仓位 / 风控阈值） |
| 4 | 改动的函数被 3 个以上调用方引用 |
| 5 | 边界条件 / 并发竞态 / 安全漏洞（逻辑类） |
| 6 | 涉及 3 个以上文件的引用链改动 |

```
调 Opus 的 prompt：
"你是黑丝（或影太极）。reforge 发现了这个问题：[描述问题]。
涉及文件：[列出文件]。
请分析修改方案，不要自己动手，告诉白纱该怎么改。"
```

**修之前：写验证标准（不管直接修还是 Opus 后修，动手前必写）**

```
问题 N：[描述]
  验证命令：[具体命令]
  预期输出：[预期结果]
```

标准没写清楚不动手。

**每处修完：Agent 三层审查**

启动 1 个 Agent（subagent_type: Explore, model: sonnet），检查：

**第一层：方案一致性**
- 要修的改动点是否全部实现？有无额外改动？

**第二层：正确性**
- 调用方是否同步更新？（grep 确认）
- 边界值（空 / 零 / 负）是否处理？

**第三层：安全性（交易系统）**
- 有无硬编码 API key？新增外部调用是否有超时？

审查输出格式：
```
方案一致性：PASS / FAIL
正确性：PASS / FAIL
安全性：PASS / FAIL
问题清单：
- [直接修] xxx — 文件 A 第 N 行
- [调Opus] xxx — 文件 B 第 N 行
```

三层全 PASS → 跑验证命令，贴输出，与预期对比。  
有 FAIL → 按意见修后重审，再跑验证命令。

- 修完（三层 PASS + 验证命令 PASS）→ 重新启动 4 个 agent
- 无问题 → `clean_count += 1`
- **连续 3 次 CLEAN → 进入 Phase 2**
- **最多 10 轮**，超过则停止并报告

✅ Phase 1 全部修复完成后：TaskUpdate Phase 1 → completed，再进 Phase 2。

## Phase 2：美容（自动循环）

启动 1 个 Agent（subagent_type: Explore, model: sonnet），纯结构改善：

- 不必要的嵌套 → 用 early return 扁平化
- 重复块 → 提取 helper
- 复杂表达式 → 拆成命名变量
- 命名改善

### 循环

- 有问题 → 修复 → 重跑
- **连续 3 次 CLEAN → 完成**
- **最多 10 轮**

✅ 完成后：TaskUpdate Phase 2 → completed，再进 Phase 3。

## Phase 3：Opus 审查

调 Opus subagent 做最终审查：

```
用 Agent 工具，model: opus，prompt:
"你是影太极（或黑丝），审查刚才 reforge 的改动：
1. 运行 git diff HEAD~1 查看实际改动
2. 逐项检查：有没有改变功能？有没有引入新 bug？有没有遗留 TODO/FIXME？每一行改动都能追溯到用户的要求吗？
3. 汇报 PASS 或 FAIL + 原因"
```

PASS → 进 Phase 4。FAIL → 按意见修改后重走 Phase 1。

✅ Opus PASS 后：TaskUpdate Phase 3 → completed，再进 Phase 4。

## Phase 4：交活前检查 + verify 维护

**Step 0：判断 verify 是否适用**

| 文件位置 | 处理 |
|---------|------|
| 有 `.wuji-root` 且找到 `*-verify.py` | 跑 `$VERIFY --post`（正常流程） |
| 不在项目目录下（如 MCP server、scripts、commands） | 写 Python 测试脚本验证逻辑，不跑 verify |

**不在项目目录时的替代验证**：

针对本次 reforge 的每个修复点，写验证脚本覆盖：
- 输入校验：非法输入是否被拒绝？
- 边界值：0 / 负数 / 最大值是否正确处理？
- 核心逻辑：函数在正常输入下输出是否符合预期？

```bash
python3 - <<'EOF'
# 针对每个修复点写一个 assert，全部 PASS 才算验证通过
import ...
assert ..., "描述"
print("所有验证 PASS")
EOF
```

**Step 1：先跑 --post 看原始结果（适用时）**
```bash
# $VERIFY 已在 Phase 0 定位，直接用
python3 "$VERIFY" --post
```
不带文件参数（reforge 是代码清理，跳过 doc sync）。

**Step 2：对照本次工作内容，分辨每一条报警**

| 报警类型 | 处理 |
|---------|------|
| 代码真问题（逻辑/反模式/竞态） | 修代码 |
| verify 配置过时（见下方） | **必须当场维护 verify，不能标遗留** |

**verify 过时 = 假遗留，必须当场修，不得推迟：**
- `CONSISTENCY_PAIRS` 里的函数不存在 → 删掉或更新为当前实际函数
- 未注册 .py 文件 → 补进 `DIR_DOC_MAP`
- `ANTI_PATTERNS` 失效条目 → 删掉或更新

**Step 3：维护完 → 再跑 --post，直到全部 ✅**

- 有新增违规 → 回 Step 1
- 全部 ✅ → git commit

✅ 完成后：TaskUpdate Phase 4 → completed，再进 Phase 4.5。

## Phase 4.5：git commit

verify 全部 ✅ 后 commit，不 push：

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

✅ commit 成功后：TaskUpdate Phase 4.5 → completed，再进完成摘要。

## 完成

### 回写知识库

完工后扫一遍：有没有值得沉淀的新知识？

```bash
# 判断标准（满足任一就写）
# - 踩了新坑、发现新规律
# - 改变了架构决策
# - 发现知识库有偏差或缺漏
```

有 → append `wiki/_incoming.md`（格式见 `/Volumes/SSD-2TB/无极开天/wiki/_incoming.md` 模板）
     然后验证知识库完整性：
     ```bash
     python3 /Volumes/SSD-2TB/无极开天/wuji-verify.py
     ```
     （绝对路径，任何 cwd 都能跑）

无 → 摘要里注明"无新知识沉淀"

### 更新文档

如果 reforge 过程中发现：
- 模块行为与文档描述不符 → 当场修正文档
- 踩坑或新知识 → 更新对应技术文档
- 新增/删除了接口 → 更新模块 README

**学到了就更新，不留到以后。**

### 完成摘要

```
🔥 回炉再造完成
   Phase 0 verify pre：✅ 基线已记录
   Phase 1 审查：X 轮（修复 N 项）
   Phase 2 美容：Y 轮（修复 M 项）
   Phase 3 Opus 审查：✅ PASS
   Phase 4 verify post：✅ 无新增违规
   文档更新：[更新了哪些文档，没有则写"无"]
   总计：X+Y 轮，全部 CLEAN
```

✅ 完成后：TaskUpdate 完成 → completed。全部任务结束。

## 规则

- 保持功能不变 — 只改 HOW 不改 WHAT
- 每次修复后 py_compile 验证
- 如果 finding 是误报或不值得改，跳过不争论
