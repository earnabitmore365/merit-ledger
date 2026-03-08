# 补齐 Gate v4.1 报告完整性

## Context
老板要求"整个架构装进一个文件夹，有目录，每一个都列出来为什么过关为什么不过关，随时能调用"。目前 `lab/results/gate_v41/gate_v41_report.db` 已有 29 张表 + gate_index 目录，但专场照妖镜 v5（135→119）的结果只打印到屏幕没存 DB，且缺一份人看的 README。

## 已有（不用动）
- gate1_* 表：有 `passed` + `reason` 字段（"不通过: 20笔 < 门槛196"）✅
- gate2_* 表：13维度成绩单 + insufficient 标记 ✅
- gate3_* 表：有 `selected` + `selected_dimensions` + `reason` 字段 ✅
- mc_results / champions：全程 MC 结果 ✅
- gate_index：29条目录 ✅

## 要做的（3步）

### 步骤1：修改 gate_mirror_v5.py，把结果写入 DB

新增 2 张表到 `gate_v41_report.db`：

```sql
-- 表1：每个候选的总览（135行）
CREATE TABLE mirror_v5_candidates (
    combo_id INTEGER PRIMARY KEY,
    strategy TEXT, coin TEXT, interval TEXT, team TEXT,
    all_pnl REAL,
    pass_wf INTEGER,      -- 至少1个考场WF通过
    pass_mc INTEGER,      -- 至少1个考场MC通过
    pass_wf_mc INTEGER    -- 至少1个考场WF+MC都通过
);

-- 表2：每个候选×3考场的明细（最多405行）
CREATE TABLE mirror_v5_pool_detail (
    combo_id INTEGER,
    pool_name TEXT,        -- 'bull'/'ranging'/'bear'
    wf_passed INTEGER,
    wf_total INTEGER,
    wf_threshold INTEGER,
    wf_ok INTEGER,
    mc_rate REAL,          -- NULL if <10 trades
    mc_trades INTEGER,
    mc_ok INTEGER,
    PRIMARY KEY (combo_id, pool_name)
);
```

修改位置：`lab/gate_mirror_v5.py` 的 main() 函数末尾，在打印结果之后加 DB 写入逻辑。

### 步骤2：重跑 gate_mirror_v5.py

执行脚本，填充 2 张新表 + 更新 gate_index（新增 2 条记录）。

### 步骤3：创建 README.md

在 `lab/results/gate_v41/README.md` 写一份人看的报告目录：
- Gate 管线流程图（初考→专考→专场WF→组考→MC→冠军）
- 每张表的说明（表名、人话描述、记录数、关键字段）
- 怎么查（常用 SQL 示例）
- 关键数字汇总（各阶段通过人数）

### 步骤4：删除旧版本
老板确认删掉 `lab/results/gate_v3/` 和 `lab/results/gate_v4/`，只留 gate_v41。

## 涉及文件
- 修改：`lab/gate_mirror_v5.py`（加 DB 写入）
- 新建：`lab/results/gate_v41/README.md`
- 写入：`lab/results/gate_v41/gate_v41_report.db`（2 新表 + gate_index 更新）

## 验证
1. 跑完后查 DB：`SELECT COUNT(*) FROM mirror_v5_candidates` = 135
2. 查 WF 通过数：`SELECT COUNT(*) FROM mirror_v5_candidates WHERE pass_wf=1` = 119
3. 查 gate_index 新增 2 条
4. README.md 存在且内容完整
