#!/bin/bash
# 系统层兜底：每小时自动清理超过 2 小时的 wuji 相关 python3 进程
# 由 launchd 定时触发，不靠人记

THRESHOLD_HOURS=2
KEYWORD="wuji-auto-trading"
LOG_PREFIX="[wuji-cleanup] $(date '+%Y-%m-%d %H:%M:%S')"

ps -eo pid,etime,command | grep "python3" | grep "$KEYWORD" | grep -v grep | \
while read pid etime cmd; do
    hours=0

    # etime 格式解析：DD-HH:MM:SS / HH:MM:SS / MM:SS
    if [[ $etime =~ ^([0-9]+)-([0-9]+):([0-9]+):([0-9]+)$ ]]; then
        hours=$(( ${BASH_REMATCH[1]} * 24 + ${BASH_REMATCH[2]} ))
    elif [[ $etime =~ ^([0-9]+):([0-9]+):([0-9]+)$ ]]; then
        hours=${BASH_REMATCH[1]}
    fi
    # MM:SS 格式 hours=0，不会被杀

    if [ "$hours" -ge "$THRESHOLD_HOURS" ]; then
        echo "$LOG_PREFIX kill pid=$pid etime=$etime"
        echo "$LOG_PREFIX cmd: $cmd"
        kill -TERM "$pid" 2>/dev/null
    fi
done

echo "$LOG_PREFIX 扫描完成"
