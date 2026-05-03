#!/usr/bin/env python3
"""
archive_daily.py — 归档超过 N 天的 daily md

遍历 ~/.claude/projects/*/memory/daily/，把文件名日期早于 cutoff 的
YYYY-MM-DD*.md 文件移动到 archive/YYYY-MM/ 目录。

默认保留最近 14 天，每天首次 SessionStart hook 调用一次（通过时间锁）。

CLI:
    archive_daily.py --dry-run        只列出将被归档的文件
    archive_daily.py --days <N>        保留天数（默认 14）
    archive_daily.py --force           忽略时间锁强制跑一次
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

SYDNEY_TZ = ZoneInfo('Australia/Sydney')
PROJECTS_BASE = os.path.expanduser('~/.claude/projects')
STATE_DIR = os.path.expanduser('~/.claude/state')
LAST_RUN_FILE = os.path.join(STATE_DIR, 'last_archive_run')
MIN_INTERVAL_HOURS = 12  # 两次归档之间至少隔 12 小时

ROLL_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2})(?:-\d+)?\.md$')


def _sydney_today():
    """返回悉尼 5AM 切日的 date 对象"""
    now = datetime.now(SYDNEY_TZ)
    if now.hour < 5:
        now = now - timedelta(days=1)
    return now.date()


def check_time_lock():
    """True = 距上次运行不足 MIN_INTERVAL_HOURS 小时，应跳过"""
    if not os.path.exists(LAST_RUN_FILE):
        return False
    try:
        with open(LAST_RUN_FILE) as f:
            last_ts = float(f.read().strip())
        now_ts = datetime.now().timestamp()
        if (now_ts - last_ts) < MIN_INTERVAL_HOURS * 3600:
            return True
    except Exception:
        pass
    return False


def update_last_run():
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LAST_RUN_FILE, 'w') as f:
            f.write(str(datetime.now().timestamp()))
    except Exception:
        pass


def archive_project(daily_dir, cutoff_date, dry_run):
    """归档单个项目的 daily 目录"""
    moved = []
    skipped = 0

    for entry in os.listdir(daily_dir):
        src = os.path.join(daily_dir, entry)
        if not os.path.isfile(src):
            continue
        m = ROLL_PATTERN.match(entry)
        if not m:
            continue
        try:
            file_date = datetime.strptime(m.group(1), '%Y-%m-%d').date()
        except Exception:
            continue
        if file_date >= cutoff_date:
            skipped += 1
            continue

        # 按月份分子目录 archive/YYYY-MM/
        archive_month_dir = os.path.join(daily_dir, 'archive', file_date.strftime('%Y-%m'))
        if not dry_run:
            os.makedirs(archive_month_dir, exist_ok=True)
        dst = os.path.join(archive_month_dir, entry)
        if dry_run:
            moved.append((src, dst))
        else:
            try:
                shutil.move(src, dst)
                moved.append((src, dst))
            except Exception as e:
                print(f'  ❌ mv {entry}: {e}', file=sys.stderr)

    return moved, skipped


def main():
    parser = argparse.ArgumentParser(description='Archive old daily md files')
    parser.add_argument('--dry-run', action='store_true', help='只列出将归档的文件')
    parser.add_argument('--days', type=int, default=14, help='保留天数（默认 14）')
    parser.add_argument('--force', action='store_true', help='忽略时间锁强制跑')
    args = parser.parse_args()

    # 时间锁
    if not args.force and not args.dry_run and check_time_lock():
        # 静默退出（被 SessionStart hook 频繁调用时不打扰）
        return 0

    today = _sydney_today()
    cutoff_date = today - timedelta(days=args.days - 1)

    total_moved = 0
    total_skipped = 0
    project_count = 0

    for proj_name in sorted(os.listdir(PROJECTS_BASE)):
        daily_dir = os.path.join(PROJECTS_BASE, proj_name, 'memory', 'daily')
        if not os.path.isdir(daily_dir):
            continue
        moved, skipped = archive_project(daily_dir, cutoff_date, args.dry_run)
        if moved or skipped:
            project_count += 1
            total_moved += len(moved)
            total_skipped += skipped
            if args.dry_run and moved:
                print(f'{proj_name}:')
                for src, dst in moved[:5]:
                    print(f'  → {os.path.basename(src)} -> archive/{os.path.basename(os.path.dirname(dst))}/')
                if len(moved) > 5:
                    print(f'  ...还有 {len(moved) - 5} 个')

    if not args.dry_run:
        update_last_run()

    mode = 'DRY-RUN' if args.dry_run else 'ARCHIVED'
    print(f'\n📦 {mode}: {total_moved} 个文件，跳过（< {args.days} 天）{total_skipped} 个，{project_count} 个项目')
    return 0


if __name__ == '__main__':
    sys.exit(main())
