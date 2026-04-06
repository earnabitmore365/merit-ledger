#!/usr/bin/env python3
"""cron 每5分钟检查通道新消息，有新消息写 channel_reminder.txt"""
import json, os, re

CHANNEL_PATH = os.path.expanduser("~/.claude/channel_taiji_liangyi.md")
MERIT_DIR = os.path.expanduser("~/.claude/merit")
CHECK_PATH = os.path.join(MERIT_DIR, "channel_check_太極.json")
REMINDER_PATH = os.path.join(MERIT_DIR, "channel_reminder.txt")

if not os.path.exists(CHANNEL_PATH):
    exit()

last_mtime = 0
if os.path.exists(CHECK_PATH):
    try:
        with open(CHECK_PATH) as f:
            last_mtime = json.load(f).get("last_mtime", 0)
    except Exception:
        pass

mtime = os.path.getmtime(CHANNEL_PATH)
if mtime <= last_mtime:
    exit()

with open(CHANNEL_PATH, encoding="utf-8") as f:
    content = f.read()

match = re.search(r'^## \[(.+?)\s+\d', content, re.MULTILINE)
if match and match.group(1).strip() == "太极":
    with open(CHECK_PATH, "w") as f:
        json.dump({"last_mtime": mtime}, f)
    exit()

lines = content.split("\n")
section_lines = []
in_section = False
for line in lines:
    if line.startswith("## ["):
        if in_section:
            break
        in_section = True
    if in_section:
        section_lines.append(line)

if section_lines:
    section = "\n".join(section_lines)[:600]
    with open(REMINDER_PATH, "w") as f:
        f.write(f"📨 通道新消息：\n{section}")

with open(CHECK_PATH, "w") as f:
    json.dump({"last_mtime": mtime}, f)
