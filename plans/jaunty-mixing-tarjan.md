# 修复下载脚本 + 每日凌晨4点自动管线

## Context

1. 下载脚本固定目标条数到了就跳过，导致 1m/5m/15m 没更新到最新
2. 老板要全周期全币种 up to date
3. 老板要每天凌晨4点自动下载+跑种子，每天自动更新

## 改动1：修复下载脚本

**文件**：`download_latest_coins_2.0.py`

`download_coin()` 函数第 138~142 行，"已达目标跳过"改成"已达目标跳过往前拉，但仍往后补最新数据"。

## 改动2：每日凌晨4点自动管线

用 crontab 设定两条定时任务（纯信号 + TTP）：

```
0 4 * * * cd /Volumes/BIWIN\ NV\ 7400\ 2TB/project/auto-trading && python3 lab/daily_pipeline.py >> lab/reports/daily_pipeline.log 2>&1
30 4 * * * cd /Volumes/BIWIN\ NV\ 7400\ 2TB/project/auto-trading && python3 lab/daily_pipeline.py --ttp >> lab/reports/daily_pipeline_ttp.log 2>&1
```

- 4:00 跑纯信号版（下载K线→增量回测→报告重算→看板）
- 4:30 跑 TTP 版（跳过下载因为4:00已下载，只跑回测→报告→看板）

日志输出到 `lab/reports/daily_pipeline.log`。

## 验证

1. 修复后跑下载，检查所有周期所有币种最新时间 ≈ 今天
2. 跑增量回测确认 1m/5m/15m combo 也有新交易
3. crontab -l 确认定时任务已设好
