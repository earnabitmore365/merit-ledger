#!/usr/bin/env python3
"""
每日摘要批处理 — launchd 凌晨 5am 触发

读昨天的 markdown 日志 → ai_call 生成标签+摘要 → 写入 conversations.db
失败 fallback：基础关键词匹配打标签，不丢数据。
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, date, timedelta

PROJECTS_BASE = os.path.expanduser("~/.claude/projects")
DB_PATH = os.path.expanduser("~/.claude/conversations.db")
MERIT_DIR = os.path.expanduser("~/.claude/merit")
LOG_PATH = "/tmp/daily_digest.log"

# 基础关键词标签（ai_call 失败时的 fallback）
TAG_WORDS = {
    '流程': ['初考', '专考', '组考', '照妖镜', '分班', '冠军', 'gate', '门槛'],
    '技术': ['回测', '种子', 'wf', 'mc', '过拟合', 'bug', '修复', '部署'],
    '市场': ['regime', '牛市', '熊市', '盘整'],
    '数据': ['k线', '下载', 'sqlite', 'duckdb', '数据库'],
    '决策': ['拍板', '决定', '砍掉', '保留', '就这样', '做吧'],
    '纠错': ['不对', '错了', '你怎么', '又忘了', '漏了'],
    '积分': ['扣分', '加分', '石卫', '天衡册', 'mission', '自审'],
}


def log(msg):
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def basic_tags(content):
    """基础关键词匹配打标签"""
    content_lower = content.lower()
    matched = set()
    for category, words in TAG_WORDS.items():
        for word in words:
            if word.lower() in content_lower:
                matched.add(category)
                break
    return list(matched)


def ai_tags_and_summary(content):
    """AI 标签+摘要（merit_gate.ai_call 已删除，始终返回 None 走 fallback）"""
    return None


def find_all_daily_dirs():
    """扫描所有项目的 daily 目录"""
    dirs = []
    try:
        for proj in os.listdir(PROJECTS_BASE):
            daily = os.path.join(PROJECTS_BASE, proj, 'memory', 'daily')
            if os.path.isdir(daily):
                dirs.append((proj, daily))
    except Exception:
        pass
    return dirs


def _sydney_yesterday_iso():
    """返回悉尼 5AM 切日的"昨天"ISO 日期字符串"""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo('Australia/Sydney'))
    if now.hour < 5:
        now = now - timedelta(days=1)
    return (now.date() - timedelta(days=1)).isoformat()


def _list_rolling_files(daily_dir, date_str):
    """当天所有滚动 md 文件按 roll index 升序（base=1）"""
    import re as _re
    if not os.path.isdir(daily_dir):
        return []
    pat = _re.compile(r'^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$')
    results = []
    for entry in os.listdir(daily_dir):
        m = pat.match(entry)
        if not m or m.group(1) != date_str:
            continue
        roll = int(m.group(2)) if m.group(2) else 1
        results.append((roll, os.path.join(daily_dir, entry)))
    results.sort(key=lambda x: x[0])
    return [p for _, p in results]


def process_yesterday():
    """处理所有项目昨天的 markdown → DB（按悉尼 5AM 切日 + 合并所有滚动文件）"""
    yesterday = _sydney_yesterday_iso()

    for proj_name, daily_dir in find_all_daily_dirs():
        md_paths = _list_rolling_files(daily_dir, yesterday)
        if not md_paths:
            continue

        # 合并所有滚动文件的内容
        contents = []
        for mp in md_paths:
            try:
                with open(mp, encoding='utf-8') as f:
                    contents.append(f.read())
            except Exception:
                continue
        content = '\n'.join(contents)

        if not content.strip():
            continue

        log(f"Processing {proj_name}/{yesterday} ({len(md_paths)} files, {len(content)} chars)")
        _process_one_day(proj_name, yesterday, content)


def _process_one_day(proj_name, yesterday, content):
    """处理单个项目单天的 markdown"""

    # 尝试 AI 标签
    ai_result = ai_tags_and_summary(content)

    if ai_result:
        tags = ",".join(ai_result["tags"])
        summary = ai_result["summary"]
        log(f"AI tags: {tags}")
    else:
        # fallback: 基础关键词
        tags = ",".join(basic_tags(content))
        # fallback 摘要：取前 200 字
        summary = content[:200].replace("\n", " ").strip()
        log(f"Fallback tags: {tags}")

    # 写入 DB
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO messages (time, speaker, content, project, session_id, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (yesterday, "系统", f"[日摘要·{proj_name}] {summary}", "daily_digest", "", tags)
        )
        conn.commit()

        # 确保索引存在
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_daily_digest ON messages(project, time)"
        )
        conn.commit()
        conn.close()
        log(f"DB written for {yesterday}: {len(summary)} chars, tags={tags}")
    except Exception as e:
        log(f"DB write failed: {e}")


if __name__ == "__main__":
    log("=== Daily digest started ===")
    process_yesterday()
    log("=== Daily digest done ===")
