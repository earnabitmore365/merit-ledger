# 计划：清理 seed_v3_ttp_highlow.db 中7个币1m镜像断点恢复标记

## 目标
删除 `seed_v3_ttp_highlow.db` 中7个币（BTC_COIN、DOT、ETH、ETH_COIN、LINK、SOL、XRP）的 1m interval、strategy LIKE '%_mirror' 且 total_trades=0 的 combo_summary 记录，以及关联的 paired_trades 记录。

## 步骤

### 步骤1：确认没有进程在写DB
```bash
lsof "/Volumes/BIWIN NV 7400 2TB/project/auto-trading/lab/reports/seed_v3_ttp_highlow.db" 2>/dev/null
```
- 已执行，退出码1，输出为空 → 确认没有进程占用 DB，可以安全操作

### 步骤2：查看受影响的combo
```python
import sqlite3
conn = sqlite3.connect('/Volumes/BIWIN NV 7400 2TB/project/auto-trading/lab/reports/seed_v3_ttp_highlow.db')
c = conn.cursor()
c.execute("""SELECT coin, strategy, total_trades FROM combo_summary
WHERE interval='1m' AND strategy LIKE '%_mirror'
AND coin IN ('BTC_COIN','DOT','ETH','ETH_COIN','LINK','SOL','XRP')
ORDER BY coin, strategy""")
rows = c.fetchall()
# 打印统计：总数、total_trades=0的数量、total_trades>0的数量
```
- 确认所有受影响combo的total_trades都是0才执行删除

### 步骤3：执行删除（仅当步骤2确认都是空的）
1. 先删 paired_trades（外键关联）
2. 再删 combo_summary

### 步骤4：验证清理结果
查询确认7个币1m镜像已全部清除

## 风险评估
- 完整性：步骤2先检查，有非0数据时不删 ✓
- 真实性：从DB直接读取，不猜 ✓
- 有效性：步骤明确，老板已给出完整SQL ✓
