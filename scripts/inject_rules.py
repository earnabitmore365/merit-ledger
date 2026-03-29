#!/usr/bin/env python3
"""
UserPromptSubmit hook: 注入 rules.md 父类规则到上下文。
只注入 <!-- INJECT START --> 和 <!-- INJECT END --> 之间的内容。
支持全局 + 项目级两份规则同时注入。
"""
import json
import os
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

cwd = data.get("cwd", os.getcwd())
home = os.path.expanduser("~")

# 项目路径编码：去掉开头 /，所有 / 换 -
project_encoded = cwd.replace("/", "-")
project_dir = os.path.join(home, ".claude", "projects", project_encoded)
if not os.path.isdir(project_dir):
    project_dir = os.path.join(home, ".claude", "projects", project_encoded.replace("_", "-"))

project_rules = os.path.join(project_dir, "memory", "rules.md")
global_rules = os.path.join(home, ".claude", "projects",
                            f"-{home.lstrip('/')}", "memory", "rules.md").replace("/", "-").replace("--", "-")

# Fallback: 找全局 rules（用户 home 目录的 projects 编码）
home_encoded = home.replace("/", "-")
global_rules = os.path.join(home, ".claude", "projects", home_encoded, "memory", "rules.md")


def extract_inject_section(path):
    """提取 INJECT START 和 INJECT END 之间的内容"""
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        content = f.read()
    start = content.find("<!-- INJECT START -->")
    end = content.find("<!-- INJECT END -->")
    if start >= 0 and end >= 0:
        return content[start + len("<!-- INJECT START -->"):end].strip()
    return ""


parts = []
seen = set()

for label, path in [
    ("全局规则", global_rules),
    ("项目规则", project_rules),
]:
    real = os.path.realpath(path)
    if real in seen or not os.path.exists(path):
        continue
    seen.add(real)
    content = extract_inject_section(path)
    if content:
        parts.append(f"=== {label} ===\n{content}")

if parts:
    print("\n---\n".join(parts))
