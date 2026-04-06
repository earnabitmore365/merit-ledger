# build_klines_indicators.py — 首尾时间戳断点检查

## 修改 1：预过滤改为首尾时间戳对比（行 203-213）

一次 SQL 查每组的 K线首尾 vs 指标首尾，不一致才进循环：

```python
check = con.execute(f'''
    SELECT coin, interval,
           MIN(time) as kline_first, MAX(time) as kline_last,
           MIN(CASE WHEN "{first_col}" IS NOT NULL THEN time END) as ind_first,
           MAX(CASE WHEN "{first_col}" IS NOT NULL THEN time END) as ind_last
    FROM klines GROUP BY coin, interval
''').fetchall()

groups = sorted(
    [(c, iv) for c, iv, kf, kl, if_, il in check
     if if_ is None or kf != if_ or kl != il],
    key=lambda g: (_IV_ORDER.get(g[1], 99), g[0]),
)
```

## 修改 2：UPDATE 只写指标为 NULL 的行（行 254-260）

WHERE 加 `AND klines."{first_col}" IS NULL`

## 验证

1. 跑 86 组（全新，ind_first=NULL → 全进循环，不变）
2. 追加测试：INSERT 1 行新 K线 → kline_last > ind_last → 只 UPDATE 新行
