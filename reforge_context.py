#!/usr/bin/env python3
"""
/reforge 上下文注入引擎
根据改动文件自动匹配项目文档+规则+踩坑记录，精化后返回注入文本。
"""
import os
import glob
import random

DOCS_DIR = "/Volumes/SSD-2TB/文档/"  # 外挂SSD物理路径，无法expanduser
MERIT_DIR = os.path.expanduser("~/.claude/merit")

# 文件名关键词 → 注入哪些文档（顾问确认版）
FILE_DOCS_MAP = {
    "adapter": ["bitmex.md"],
    "gateway": ["bitmex.md"],
    "feed_gateway": ["bitmex.md"],
    "strategy_runner": ["bitmex.md"],
    "generate_seed": ["sqlite.md", "duckdb.md", "segmented_backtest.md"],
    "build_seed_report": ["duckdb.md", "seed_report_field_reference.md"],
    "build_klines": ["duckdb.md"],
    "merit_gate": ["claude_code.md", "minimax_api.md"],
    "credit_manager": ["claude_code.md"],
    "session_start": ["claude_code.md"],
    "evolve": ["minimax_api.md"],
    "backtest": ["duckdb.md", "segmented_backtest.md"],
    "incremental_backtest": ["duckdb.md", "segmented_backtest.md"],
    "verify_seed": ["duckdb.md"],
    "hyperliquid": ["hyperliquid.md"],
    "binance": ["binance.md"],
    "bybit": ["bybit.md"],
    "bitget": ["bitget.md"],
}


def get_rules_for_grep():
    """从 rules.md INJECT 区提取能 grep 检查的规则（排除纯行为规范）"""
    grep_keywords = ["路径", "硬编码", "import", "绝对", "相对", "调用", "写死",
                     "配置", "常量", "文档", "同步", "备份", "verify"]
    rules = []
    # 搜两个 rules.md
    for rules_path in [
        os.path.expanduser("~/.claude/projects/-Users-allenbot/memory/rules.md"),
        os.path.expanduser("~/.claude/projects/-Volumes-SSD-2TB-project-auto-trading/memory/rules.md"),
    ]:
        if not os.path.exists(rules_path):
            continue
        try:
            with open(rules_path, encoding="utf-8") as f:
                in_inject = False
                for line in f:
                    if "INJECT" in line.upper() or "inject" in line:
                        in_inject = True
                        continue
                    if in_inject and line.startswith("#"):
                        break
                    if in_inject and line.strip():
                        if any(kw in line for kw in grep_keywords):
                            rules.append(line.strip())
        except Exception:
            pass
    return rules[:20]  # 最多 20 条


def get_recent_lessons(limit=20):
    """读 LEARNINGS.md 最近 N 条"""
    path = os.path.join(MERIT_DIR, "learnings", "LEARNINGS.md")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        return lines[-limit:]
    except Exception:
        return []


def get_anti_patterns():
    """从 wuji-verify.py 提取 ANTI_PATTERNS 列表"""
    vpath = os.path.join(MERIT_DIR, "wuji-verify.py")
    if not os.path.exists(vpath):
        return []
    patterns = []
    try:
        with open(vpath, encoding="utf-8") as f:
            in_ap = False
            for line in f:
                if "ANTI_PATTERNS" in line and "=" in line:
                    in_ap = True
                    continue
                if in_ap:
                    if line.strip().startswith("]"):
                        break
                    if line.strip().startswith("(") or line.strip().startswith('"'):
                        patterns.append(line.strip().strip(",").strip())
        return patterns[:15]
    except Exception:
        return []


def get_docs_for_files(file_paths):
    """根据改动文件匹配需要注入的文档，返回 {doc_name: content_excerpt}"""
    needed_docs = set()
    for fp in file_paths:
        basename = os.path.splitext(os.path.basename(fp))[0]
        for keyword, docs in FILE_DOCS_MAP.items():
            if keyword in basename:
                needed_docs.update(docs)

    doc_contents = {}
    for doc_name in needed_docs:
        doc_path = os.path.join(DOCS_DIR, doc_name)
        if os.path.exists(doc_path):
            try:
                with open(doc_path, encoding="utf-8") as f:
                    content = f.read()
                # 只取踩坑记录和关键规则部分（搜索 "坑" "注意" "踩" "禁止" "必须"）
                important_lines = []
                for line in content.split("\n"):
                    if any(kw in line for kw in ["坑", "注意", "踩", "禁止", "必须", "不要", "WARNING", "⚠", "❌"]):
                        important_lines.append(line.strip())
                if important_lines:
                    doc_contents[doc_name] = "\n".join(important_lines[:30])
            except Exception:
                pass
    return doc_contents


def build_context(file_paths):
    """构建完整注入上下文"""
    sections = []

    # 1. 项目规则
    rules = get_rules_for_grep()
    if rules:
        sections.append("## 项目规则（必须遵守）\n" + "\n".join(f"- {r}" for r in rules))

    # 2. 踩坑记录
    lessons = get_recent_lessons()
    if lessons:
        picks = random.sample(lessons, min(10, len(lessons)))
        sections.append("## 踩坑记录（血的教训）\n" + "\n".join(f"- {l}" for l in picks))

    # 3. ANTI_PATTERNS
    aps = get_anti_patterns()
    if aps:
        sections.append("## 反模式检查（自动 grep 的项目）\n" + "\n".join(f"- {a}" for a in aps))

    # 4. 相关文档
    docs = get_docs_for_files(file_paths)
    if docs:
        for name, content in docs.items():
            sections.append(f"## 参考文档：{name}（踩坑+关键规则）\n{content}")

    return "\n\n".join(sections) if sections else ""


if __name__ == "__main__":
    import sys
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    ctx = build_context(files)
    if ctx:
        print(ctx)
    else:
        print("（无匹配上下文）")
