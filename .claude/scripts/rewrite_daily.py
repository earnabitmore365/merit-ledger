#!/usr/bin/env python3
"""
rewrite_daily.py — 历史 daily md 重生成脚本

从 ~/.claude/projects/*/*.jsonl 读取最近 N 天（默认 14）的会话消息，
按新格式重新生成所有 daily md（两阶段提交 + 错误日志）。

新格式：
- 悉尼 5AM 切日
- 只保留 user.text + assistant.text（剔除 tool_use）
- 每条消息附 jsonl 锚点 <!-- jsonl: rel_path#L<s>-L<e> -->
- 超过 500 行滚动到 YYYY-MM-DD-002.md

两阶段提交：
- 阶段 1: 写到 /tmp/daily_new/<project>/<date>.md
- 阶段 2: 全部成功后 mv 到 ~/.claude/projects/<project>/memory/daily/

CLI:
    rewrite_daily.py --dry-run             # 只统计不写
    rewrite_daily.py --date 2026-04-10     # 只处理指定日期
    rewrite_daily.py --days 14             # 处理最近 N 天（默认 14）
    rewrite_daily.py --project <name>      # 只处理指定项目
"""

import argparse
import json
import os
import re
import sys
import shutil
from datetime import datetime, timedelta, timezone
from collections import defaultdict

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

SYDNEY_TZ = ZoneInfo('Australia/Sydney')
PROJECTS_BASE = os.path.expanduser('~/.claude/projects')
TMP_NEW_DIR = '/tmp/daily_new'
ERROR_LOG = '/tmp/rewrite_daily_errors.log'
DAILY_ROLL_LINES = 500

# 跟 db_write.py 保持一致
SKIP_DIRS = {
    '-Users-allenbot--claude',
    '-private-tmp-claude-evolver',
    '-Users-allenbot--openclaw-workspace',
}

TAIJI_PROJECT = '-Users-allenbot'


def log_error(msg):
    try:
        with open(ERROR_LOG, 'a') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def get_daily_date(dt):
    """悉尼 5AM 切日"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    sydney = dt.astimezone(SYDNEY_TZ)
    if sydney.hour < 5:
        sydney = sydney - timedelta(days=1)
    return sydney.strftime('%Y-%m-%d')


def build_jsonl_anchor(rel_path, line_start, line_end):
    return f'<!-- jsonl: {rel_path}#L{line_start}-L{line_end} -->'


def parse_jsonl_messages(jsonl_path, is_taiji=False):
    """解析 jsonl，返回结构化消息列表

    每条：{speaker, text, timestamp_dt, line_no}
    - 只保留有 text 的消息
    - 剔除 tool_use 块
    """
    messages = []
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_no_0, raw_line in enumerate(f):
                line_no = line_no_0 + 1  # 1-based
                try:
                    obj = json.loads(raw_line)
                except Exception:
                    continue
                msg_type = obj.get('type', '')
                ts_str = obj.get('timestamp', '')
                if not ts_str:
                    continue
                try:
                    ts_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                except Exception:
                    continue

                if msg_type == 'user':
                    content = obj.get('message', {}).get('content')
                    text = ''
                    if isinstance(content, str):
                        text = content.strip()
                    elif isinstance(content, list):
                        texts = []
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                texts.append(block.get('text', '').strip())
                        text = '\n'.join(t for t in texts if t)
                    if text and not text.startswith('[Request'):
                        speaker = '无极' if is_taiji else '执事'
                        messages.append({
                            'speaker': speaker,
                            'text': text,
                            'timestamp': ts_dt,
                            'line_no': line_no,
                        })

                elif msg_type == 'assistant':
                    msg = obj.get('message', {})
                    model = msg.get('model', '')
                    if 'opus' in model:
                        speaker = '太极' if is_taiji else '白纱'
                    elif 'sonnet' in model:
                        speaker = '影太极' if is_taiji else '黑丝'
                    else:
                        speaker = '太极' if is_taiji else '白纱'
                    blocks = msg.get('content', [])
                    text_parts = []
                    for b in blocks:
                        if not isinstance(b, dict):
                            continue
                        if b.get('type') == 'text' and b.get('text', '').strip():
                            text_parts.append(b['text'].strip())
                    text = '\n'.join(text_parts).strip()
                    if text:
                        messages.append({
                            'speaker': speaker,
                            'text': text,
                            'timestamp': ts_dt,
                            'line_no': line_no,
                        })
    except Exception as e:
        log_error(f'parse {jsonl_path}: {e}')
    return messages


def format_block(msg, rel_path):
    """格式化为 markdown block"""
    sydney_dt = msg['timestamp'].astimezone(SYDNEY_TZ)
    time_label = sydney_dt.strftime('%H:%M:%S')
    anchor = build_jsonl_anchor(rel_path, msg['line_no'], msg['line_no'])
    return (
        f"## {time_label} | {msg['speaker']}\n"
        f"{anchor}\n\n"
        f"{msg['text']}\n\n"
        f"---\n"
    )


def get_project_jsonl_files(project_dir, cutoff_dt, specific_date=None):
    """返回项目下的所有 jsonl 文件路径，按 mtime 筛选（cutoff_dt 之后的）"""
    results = []
    try:
        for fname in os.listdir(project_dir):
            if not fname.endswith('.jsonl'):
                continue
            fpath = os.path.join(project_dir, fname)
            try:
                mtime = os.path.getmtime(fpath)
                mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                if mtime_dt >= cutoff_dt:
                    results.append(fpath)
            except Exception:
                continue
    except Exception:
        pass
    return results


def write_rolling_md(output_dir, date_str, blocks_text, is_first_write_for_date):
    """写入 md 文件，超 DAILY_ROLL_LINES 行滚动

    blocks_text: 要追加的内容（可能跨多个消息）
    is_first_write_for_date: 是否是本次处理该日期的第一次写入（决定是否写文件头）
    """
    pat = re.compile(r'^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$')
    base_name = f'{date_str}.md'

    # 找当前最大 roll
    existing = []
    if os.path.isdir(output_dir):
        for entry in os.listdir(output_dir):
            m = pat.match(entry)
            if m and m.group(1) == date_str:
                roll = int(m.group(2)) if m.group(2) else 1
                existing.append((roll, entry))
    existing.sort(key=lambda x: x[0])

    if existing:
        current_roll, current_name = existing[-1]
        current_path = os.path.join(output_dir, current_name)
        # 检查当前文件行数
        with open(current_path, 'r', encoding='utf-8') as f:
            current_lines = sum(1 for _ in f)
    else:
        current_roll = 1
        current_name = base_name
        current_path = os.path.join(output_dir, current_name)
        current_lines = 0

    # 如果超过上限，滚动到新文件
    if current_lines >= DAILY_ROLL_LINES:
        new_roll = current_roll + 1
        current_path = os.path.join(output_dir, f'{date_str}-{new_roll:03d}.md')
        current_lines = 0

    # 写入（新文件加文件头）
    is_new_file = not os.path.exists(current_path)
    with open(current_path, 'a', encoding='utf-8') as f:
        if is_new_file:
            f.write(f"# {date_str} (Sydney AEST/AEDT)\n\n")
        f.write(blocks_text)


def process_project(project_dir_name, cutoff_dt, specific_date, stats, dry_run):
    """处理单个项目"""
    project_dir = os.path.join(PROJECTS_BASE, project_dir_name)
    if not os.path.isdir(project_dir):
        return
    if project_dir_name in SKIP_DIRS:
        return

    jsonl_files = get_project_jsonl_files(project_dir, cutoff_dt)
    stats['jsonl_files'] += len(jsonl_files)

    is_taiji = (project_dir_name == TAIJI_PROJECT)

    # 收集所有消息，按日期分组
    # dated_messages: {date_str: [(msg, rel_path), ...]}
    dated_messages = defaultdict(list)

    for jsonl_path in jsonl_files:
        rel_path = os.path.relpath(jsonl_path, PROJECTS_BASE)
        msgs = parse_jsonl_messages(jsonl_path, is_taiji=is_taiji)
        stats['total_messages'] += len(msgs)
        for m in msgs:
            date_str = get_daily_date(m['timestamp'])
            if date_str < cutoff_date_str:
                continue
            if specific_date and date_str != specific_date:
                continue
            dated_messages[date_str].append((m, rel_path))

    # 每个日期内按时间戳排序
    for date_str in dated_messages:
        dated_messages[date_str].sort(key=lambda x: (x[0]['timestamp'], x[0]['line_no']))

    stats['dates_per_project'][project_dir_name] = len(dated_messages)

    if dry_run:
        for date_str, msgs in dated_messages.items():
            stats['dates_written'].add((project_dir_name, date_str))
            stats['total_blocks_per_date'][(project_dir_name, date_str)] = len(msgs)
        return

    # 写入临时目录
    output_dir = os.path.join(TMP_NEW_DIR, project_dir_name, 'memory', 'daily')
    os.makedirs(output_dir, exist_ok=True)

    for date_str, msgs in sorted(dated_messages.items()):
        # 分批写入以触发滚动：先一批 400 个块看看
        # 简化：每次 write_rolling_md 写一个 block，让滚动自然发生
        for i, (msg, rel_path) in enumerate(msgs):
            block_text = format_block(msg, rel_path)
            write_rolling_md(output_dir, date_str, block_text, is_first_write_for_date=(i == 0))
        stats['dates_written'].add((project_dir_name, date_str))


def main():
    parser = argparse.ArgumentParser(description='Rewrite daily md from jsonl source')
    parser.add_argument('--dry-run', action='store_true', help='只统计不写')
    parser.add_argument('--date', help='只处理指定日期 YYYY-MM-DD')
    parser.add_argument('--days', type=int, default=14, help='处理最近 N 天（默认 14）')
    parser.add_argument('--project', help='只处理指定项目')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    # 计算 cutoff
    # 用悉尼时区确定"今天"，往前推 N 天
    now_syd = datetime.now(SYDNEY_TZ)
    if now_syd.hour < 5:
        now_syd = now_syd - timedelta(days=1)
    today = now_syd.date()
    cutoff_date = today - timedelta(days=args.days - 1)

    global cutoff_date_str
    cutoff_date_str = cutoff_date.isoformat()

    # jsonl 文件 mtime 筛选：保留 > cutoff_date 00:00 Sydney 之前的文件
    cutoff_dt = datetime.combine(cutoff_date, datetime.min.time(), tzinfo=SYDNEY_TZ)

    stats = {
        'jsonl_files': 0,
        'total_messages': 0,
        'dates_written': set(),
        'dates_per_project': {},
        'total_blocks_per_date': {},
    }

    # 清理临时目录
    if not args.dry_run:
        if os.path.exists(TMP_NEW_DIR):
            shutil.rmtree(TMP_NEW_DIR)
        os.makedirs(TMP_NEW_DIR)

    # 清理旧的 error log
    if os.path.exists(ERROR_LOG):
        os.remove(ERROR_LOG)

    # 处理项目
    if args.project:
        process_project(args.project, cutoff_dt, args.date, stats, args.dry_run)
    else:
        for proj_name in sorted(os.listdir(PROJECTS_BASE)):
            if proj_name in SKIP_DIRS:
                continue
            proj_path = os.path.join(PROJECTS_BASE, proj_name)
            if not os.path.isdir(proj_path):
                continue
            process_project(proj_name, cutoff_dt, args.date, stats, args.dry_run)

    # 报告
    print(f"\n{'=' * 60}")
    print(f"Rewrite Daily Report")
    print(f"{'=' * 60}")
    print(f"模式: {'DRY-RUN' if args.dry_run else 'WRITE'}")
    print(f"时间范围: 最近 {args.days} 天 (cutoff={cutoff_date_str})")
    if args.date:
        print(f"只处理日期: {args.date}")
    if args.project:
        print(f"只处理项目: {args.project}")
    print(f"")
    print(f"扫描 jsonl 文件: {stats['jsonl_files']}")
    print(f"总消息数: {stats['total_messages']}")
    print(f"生成 daily md 日期: {len(stats['dates_written'])}")
    print(f"")
    print(f"按项目分:")
    for proj, count in sorted(stats['dates_per_project'].items()):
        if count > 0:
            print(f"  {proj}: {count} 个日期")
    if args.dry_run:
        print(f"\n前 10 个日期 (project, date, blocks):")
        for i, ((proj, date_str), count) in enumerate(sorted(stats['total_blocks_per_date'].items())[:10]):
            print(f"  {proj} / {date_str}: {count} blocks")
    if not args.dry_run:
        print(f"\n输出目录: {TMP_NEW_DIR}")
    if os.path.exists(ERROR_LOG):
        err_count = sum(1 for _ in open(ERROR_LOG))
        print(f"\n⚠️ 错误日志: {ERROR_LOG} ({err_count} 条)")


if __name__ == '__main__':
    main()
