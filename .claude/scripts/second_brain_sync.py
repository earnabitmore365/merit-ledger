#!/usr/bin/env python3
"""
第二大脑 Stop hook — daily sync
对话结束时把今天的 daily roll 文件原样 copy 到 wiki vault raw/conversations/{agent}/。
不修改文件内容，不合并 roll，不调 AI。
"""
import json
import pathlib
import shutil
import sys
from datetime import datetime

VAULT_RAW = pathlib.Path("/Volumes/SSD-2TB/无极开天/raw/conversations")

AGENT_MAP = [
    ("-Users-allenbot--claude-merit", "merit",
     pathlib.Path.home() / ".claude/projects/-Users-allenbot--claude-merit/memory/daily"),
    ("auto-trading", "auto-trading",
     pathlib.Path.home() / ".claude/projects/-Volumes-SSD-2TB-project-auto-trading/memory/daily"),
    ("-Users-allenbot/", "taiji",
     pathlib.Path.home() / ".claude/projects/-Users-allenbot/memory/daily"),
]


def infer_agent(transcript_path: str):
    for marker, agent, daily_dir in AGENT_MAP:
        if marker in transcript_path:
            return agent, daily_dir
    return None, None


def copy_today_daily(agent: str, daily_dir: pathlib.Path) -> list[str]:
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    dest_dir = VAULT_RAW / agent
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for src in sorted(daily_dir.glob(f"{today}*.md")):
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        copied.append(src.name)
    return copied


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        data = {}

    try:
        transcript_path = data.get("transcript_path", "")
        agent, daily_dir = infer_agent(transcript_path)
        if not agent or not daily_dir or not daily_dir.exists():
            return
        if not VAULT_RAW.exists():
            return
        copy_today_daily(agent, daily_dir)
    except Exception:
        pass  # 静默降级，Stop hook 失败不阻塞对话


if __name__ == "__main__":
    main()
