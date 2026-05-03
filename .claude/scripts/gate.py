#!/usr/bin/env python3
"""
gate.py — PreToolUse hook 统一入口
合并 redflag（红旗词检测）+ docmap（文档映射检查）+ skillsgate（skill 加载拦截）。

替代：redflag_hook.py + docmap_hook.py + pine_gate.py
"""
import json
import os
import re
import sys

# ── 共享工具 ────────────────────────────────────────────────────────────

_DOC_MAP_PATH = os.path.expanduser("~/.claude/scripts/doc_map.json")
_SKILL_PATH = os.path.expanduser("~/.claude/skills/pine/SKILL.md")
_MCP_TOOLS = {"pine_read_docs", "pine_render", "pine_validate", "pine_write"}
_MARKER = os.path.expanduser("~/.claude/.pine_skill_loaded")


# ═══════════════════════════════════════════════════════════════════════
# redflag — 红旗词检测
# ═══════════════════════════════════════════════════════════════════════

RED_FLAGS = [
    {"type": "intent_guess", "words": ["显然", "顺手", "应该是要", "可能老祖", "看起来是要", "理所当然"],
     "msg": "🚩 检测到意图猜测词「{word}」。\n停下来问执事，不自行处理。"},
    {"type": "tech_guess", "words": ["应该能跑", "应该没问题", "应该不会", "应该可以", "应该已经"],
     "msg": "🚩 检测到技术猜测词「{word}」。\n停下来跑命令验证，贴输出。"},
    {"type": "tech_uncertain", "words": ["可能", "感觉", "大概", "估计", "似乎"],
     "msg": "🚩 检测到技术不确定词「{word}」。\n调黑丝（Opus subagent）讨论。"},
    {"type": "leftover", "words": ["不影响", "不重要", "暂时", "先跳过", "稍后", "基本上", "没关系"],
     "msg": "🚩 检测到遗留信号词「{word}」。\n立刻用 TaskCreate 登记，不跳过。"},
]

_CACHE_UUID = os.path.expanduser("~/.claude/.redflag_last_uuid")


def _get_last_assistant(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return "", ""
    text, uid = "", ""
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") != "assistant":
                        continue
                    msg = obj.get("message", {})
                    content = msg.get("content", [])
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                        if texts:
                            text = " ".join(texts)
                    uid = obj.get("uuid", "")
                except Exception:
                    continue
    except Exception:
        return "", ""
    return text, uid


def _strip_md(t):
    t = re.sub(r'```.*?```', '', t, flags=re.DOTALL)
    t = re.sub(r'`[^`\n]+`', '', t)
    t = re.sub(r'\|[^\n]+\|', '', t)
    t = re.sub(r'「[^」]*」|『[^』]*』', '', t)
    t = re.sub(r'"[^"\n]{1,50}"', '', t)
    t = re.sub(r'^>.*$', '', t, flags=re.MULTILINE)
    return t


def _scan_redflags(text):
    if not text:
        return []
    text = _strip_md(text)
    hits = []
    for flag in RED_FLAGS:
        for word in flag["words"]:
            if word in text:
                hits.append(flag["msg"].format(word=word))
                break
    return hits


def _was_reported(uid):
    try:
        if os.path.exists(_CACHE_UUID):
            return open(_CACHE_UUID).read().strip() == uid
    except Exception:
        pass
    return False


def _mark_reported(uid):
    try:
        with open(_CACHE_UUID, "w") as f:
            f.write(uid)
    except Exception:
        pass


def check_redflag(data):
    tp = data.get("transcript_path", "")
    txt, uid = _get_last_assistant(tp)
    if not txt:
        return None
    if uid and _was_reported(uid):
        return None
    hits = _scan_redflags(txt)
    if not hits:
        return None
    if uid:
        _mark_reported(uid)
    alerts = "\n\n".join(hits)
    return f"⚠️ 红旗词检测（{len(hits)} 条）：\n\n{alerts}\n\n请按上述提示处理后再继续。"


# ═══════════════════════════════════════════════════════════════════════
# docmap — 文档映射检查
# ═══════════════════════════════════════════════════════════════════════

def _load_doc_map():
    try:
        with open(_DOC_MAP_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return {k: v for k, v in d.items() if not k.startswith("_")}
    except Exception:
        return {}


def _was_doc_read(required, transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return False
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "assistant":
                        for c in (obj.get("message", {}).get("content", []) or []):
                            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Read":
                                fp = c.get("input", {}).get("file_path", "")
                                if os.path.basename(required) in fp or fp in required:
                                    return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def check_docmap(data):
    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        return None
    fp = data.get("tool_input", {}).get("file_path", "")
    if not fp:
        return None
    doc_map = _load_doc_map()
    required = None
    for pattern, doc in doc_map.items():
        if pattern in fp:
            required = doc
            break
    if not required:
        return None
    if _was_doc_read(required, data.get("transcript_path", "")):
        return None
    return (
        f"⚠️ doc_map 路由提醒：\n\n"
        f"你正在修改 `{os.path.basename(fp)}`，"
        f"但本次 session 尚未读过对应文档：\n  {required}\n\n"
        f"请先 Read 该文档后再继续。"
    )


# ═══════════════════════════════════════════════════════════════════════
# skillsgate — skill 加载拦截
# ═══════════════════════════════════════════════════════════════════════

def check_skillsgate(data):
    tool_name = data.get("tool_name", "")

    # Skill 工具加载了 pine → 创建标记
    if tool_name == "Skill":
        inp = data.get("tool_input", {})
        combined = str(inp).lower()
        if "pine" in combined:
            open(_MARKER, "w").close()
        return None

    # Read SKILL.md → 创建标记
    if tool_name == "Read":
        path = data.get("tool_input", {}).get("file_path", "")
        try:
            if os.path.abspath(os.path.expanduser(path)) == _SKILL_PATH:
                open(_MARKER, "w").close()
        except Exception:
            pass
        return None

    # 非 pine 工具 → 放行
    if tool_name not in _MCP_TOOLS:
        return None

    # pine_* 工具 → 检查标记
    if os.path.exists(_MARKER):
        return None

    return "⛔ pine_gate 拦截：必须先输入 /pine 加载 skill，才能调 pine_* 工具。"


# ═══════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # 按顺序执行检查（第一条命中的返回提醒，不继续往下）
    for check in (check_skillsgate, check_docmap, check_redflag):
        msg = check(data)
        if msg:
            event = data.get("hook_event_name", "PreToolUse")
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": msg,
                }
            }, ensure_ascii=False))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
