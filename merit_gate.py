#!/usr/bin/env python3
"""
石卫 v7 — 无极堂·天衡册 统一引擎

合并：merit_gate(PreToolUse) + merit_judge(Stop/UserPromptSubmit)
      + merit_post_audit(PostToolUse) + reflect_hook + ai_call + py_compile

一个文件管全部天衡册逻辑，按 hook_event_name 分支。
石卫既是守门人，也是判官、教练、审计员。
知情放行 + 押金制 + 自动打分 + reflect 合体 + 自进化。

┌─ 结构索引（改动前先看这里，改完后必须更新行号）─────────┐
│                                                         │
│  石卫日志+段位   L109-L188  log_shiwei_action/credit       │
│  AI 调用(Sonnet) L190-L296  ai_call/sonnet/minimax/pending │
│  待审列表        L251-L277  log_pending_review             │
│  CHANGELOG      L300-L407   record_changelog_op/flush      │
│  等级+积分+记录 L408-L596   get_level / update_credit      │
│  打分表(归零)    L597-L607  SCORING_TABLE(只检测不扣分)    │
│  Mission 计划   L614-L763   load/save/planned/audit        │
│  输出函数       L765-L793   output_deny / output_ask       │
│  硬规则检查     L795-L1107  destructive/read/grep/agent    │
│  PreToolUse     L1109-L1237 handle_pre_tool_use            │
│  PostToolUse    L1239-L1347 verify+mission+changelog       │
│  通道检查       L1348-L1437 check_channel                  │
│  UserPromptSubmit L1438-L1560 語気暂停+任务標記            │
│  Stop 辅助      L1562-L1785 計數器+pending+context+自审    │
│  Stop 评分      L1786-L1830 handle_stop(冷却+AI評估)       │
│  evolve 触发    L1830-L1860 _try_evolve（cron 每5分鐘）    │
│  Reflect 合体   L1860-L2010 trigger追踪+习惯               │
│  Main 入口      L2050+      hook_event_name 分支           │
│  review-plan    L2100+      CLI --review-plan              │
│  後台評分       L2260+      _run_bg_stop_eval(待审列表)    │
│                                                         │
│  改拦截规则？    → L1109 handle_pre_tool_use               │
│  改打分表？      → L597 SCORING_TABLE                      │
│  改 mission？    → L614 load_mission                       │
│  改评分逻辑？    → L1786 handle_stop                       │
│  改 reflect？    → L1940 auto_reflect_and_evolve           │
│  改自审检测？    → L1711 check_self_audit                  │
│  改石卫日志？    → L109 log_shiwei_action                  │
│  改 review-plan？→ L2100+ review_plan                      │
│  改 CHANGELOG？  → L300 _resolve_changelog_path/flush      │
│  改语气识别？    → L1454 judge_user_sentiment(暂停)        │
│                                                         │
│  ⚠️ 铁律：改完本文件必须同步更新此索引的行号            │
└─────────────────────────────────────────────────────────┘
"""

import fcntl
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

# ══════════════════════════════════════════════════════
#  路径常量
# ══════════════════════════════════════════════════════

MERIT_DIR = os.path.expanduser("~/.claude/merit")
CREDIT_PATH = os.path.join(MERIT_DIR, "credit.json")
LEARNINGS_PATH = os.path.join(MERIT_DIR, "learnings", "LEARNINGS.md")
SHIWEI_LOG_DIR = os.path.join(MERIT_DIR, "shiwei_log")
SHIWEI_CREDIT_PATH = os.path.join(MERIT_DIR, "shiwei_credit.json")
MISSION_PATH = os.path.join(MERIT_DIR, "mission.json")  # fallback 旧路径

# 积分上限
MAX_SCORE = 10000
MAX_SHIWEI_SCORE = 100

# Mission 状态常量
MS_PENDING = "pending"
MS_ACTIVE = "active"
MS_COMPLETED = "completed"
MS_ABORTED = "aborted"

# 当前 agent（hook 入口设置，全局缓存）
_current_agent = ""

CHANNEL_PATH = os.path.expanduser("~/.claude/channel_taiji_liangyi.md")  # 通道文件不属于天衡册
CHANNEL_CHECK_PATH = os.path.join(MERIT_DIR, "channel_check.json")
SNAPSHOT_PATH = os.path.join(MERIT_DIR, "file_snapshot.json")
VIOLATIONS_PATH = os.path.join(MERIT_DIR, "violations.jsonl")
PENDING_TASK_PATH = os.path.join(MERIT_DIR, "pending_task.json")
PENDING_REVIEW_PATH = os.path.join(MERIT_DIR, "pending_review.jsonl")
STOP_COUNTER_PATH = os.path.join(MERIT_DIR, "stop_counter.json")
DELETE_WHITELIST_PATH = os.path.join(MERIT_DIR, "delete_whitelist.json")
DB_PATH = os.path.expanduser("~/.claude/conversations.db")  # 通讯部文件不属于天衡册
PENDING_CHANGELOG_PATH = os.path.join(MERIT_DIR, "pending_changelog_ops.jsonl")

DEFAULT_CHANGELOG = os.path.expanduser("~/.claude/projects/-Users-allenbot/memory/CHANGELOG.md")


# ══════════════════════════════════════════════════════
#  石卫操作日志 + 石卫段位
# ══════════════════════════════════════════════════════

SHIWEI_RANKS = [
    (95, "钻石"), (80, "铂金"), (60, "黄金"),
    (40, "白银"), (20, "青铜"), (0, "黑铁"),
]


def log_shiwei_action(action_type, target, operation, rule, result, detail="", ai_raw=""):
    """追加写入石卫操作日志（按天 md）"""
    try:
        os.makedirs(SHIWEI_LOG_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(SHIWEI_LOG_DIR, f"{today}.md")
        now = datetime.now().strftime("%H:%M")
        mission = load_mission()
        mission_name = mission.get("mission", "")[:40] if mission else ""

        entry = f"\n### {now} | {action_type} | {result}\n"
        entry += f"- **对象**: {target}\n"
        entry += f"- **操作**: {operation}\n"
        entry += f"- **规则**: {rule}\n"
        entry += f"- **结果**: {result}\n"
        if mission_name:
            entry += f"- **mission**: {mission_name}\n"
        if detail:
            entry += f"- **详情**: {detail}\n"
        if ai_raw:
            entry += f"- **AI原始返回**: {ai_raw}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def load_shiwei_credit():
    """读石卫积分"""
    if not os.path.exists(SHIWEI_CREDIT_PATH):
        return {"score": 0, "rank": "黑铁", "history": []}
    try:
        with open(SHIWEI_CREDIT_PATH) as f:
            return json.load(f)
    except Exception:
        return {"score": 0, "rank": "黑铁", "history": []}


def get_shiwei_rank(score):
    for threshold, rank in SHIWEI_RANKS:
        if score >= threshold:
            return rank
    return "黑铁"


def update_shiwei_credit(delta, reason, auditor="太极"):
    """更新石卫积分+段位"""
    if delta == 0:
        return
    data = load_shiwei_credit()
    old_score = data["score"]
    new_score = max(0, min(MAX_SHIWEI_SCORE, old_score + delta))
    data["score"] = new_score
    data["rank"] = get_shiwei_rank(new_score)
    data.setdefault("history", []).append({
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "delta": delta,
        "reason": reason,
        "auditor": auditor,
        "score_after": new_score,
    })
    if len(data["history"]) > 100:
        data["history"] = data["history"][-100:]
    try:
        with open(SHIWEI_CREDIT_PATH, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ══════════════════════════════════════════════════════
#  AI 调用（内联 ai_call.py）
# ══════════════════════════════════════════════════════

_MINIMAX_KEY_PATH = os.path.expanduser("~/.claude/.minimax_key")
_MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
_MINIMAX_MODEL = "MiniMax-M2.7-highspeed"
PENDING_AI_TASKS_PATH = os.path.join(MERIT_DIR, "pending_ai_tasks.jsonl")


def ai_call(prompt, system=None, max_tokens=4096, timeout=30):
    """调 Sonnet（默认）或 MiniMax（fallback）。失败返回空。

    默认走 claude --model sonnet --print。
    设 MERIT_USE_MINIMAX=1 环境变量可切回 MiniMax。
    """
    if os.environ.get("MERIT_USE_MINIMAX") == "1":
        return _ai_call_minimax(prompt, system, max_tokens, timeout)
    return _ai_call_sonnet(prompt, system, timeout)


def _ai_call_sonnet(prompt, system=None, timeout=120):
    """通过 claude CLI 调 Sonnet（stdin 传 prompt，MERIT_SUBPROCESS=1 防子进程触发扣分）"""
    try:
        import subprocess as _sp
        cmd = ["claude", "--model", "sonnet", "--print", "--max-turns", "1"]
        if system:
            prompt = f"[System]\n{system}\n\n[User]\n{prompt}"
        env = dict(os.environ, MERIT_SUBPROCESS="1")
        result = _sp.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, env=env)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _ai_call_minimax(prompt, system=None, max_tokens=4096, timeout=30):
    """SDK 直调 MiniMax（fallback）"""
    try:
        import anthropic
    except ImportError:
        return ""
    if not os.path.exists(_MINIMAX_KEY_PATH):
        return ""
    try:
        with open(_MINIMAX_KEY_PATH) as kf:
            key = kf.read().strip()
        client = anthropic.Anthropic(api_key=key, base_url=_MINIMAX_BASE_URL, timeout=timeout)
        kwargs = {"model": _MINIMAX_MODEL, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        for block in resp.content:
            if getattr(block, "type", "") == "text":
                return block.text.strip()
        for block in resp.content:
            if getattr(block, "type", "") == "thinking":
                thinking = getattr(block, "thinking", "")
                if not thinking:
                    continue
                start = thinking.find("{")
                end = thinking.rfind("}") + 1
                if start >= 0 and end > start:
                    return thinking[start:end]
                lines = [l.strip() for l in thinking.split('\n') if l.strip()]
                if lines:
                    return lines[-1]
        return ""
    except Exception:
        return ""


def log_pending_review(agent, event, detail=""):
    """写入待审列表（只奖不罚制：不扣分，等老祖裁决）"""
    path = os.path.join(MERIT_DIR, "pending_review.json")
    try:
        import fcntl
        if not os.path.exists(path):
            with open(path, "w") as init_f:
                json.dump([], init_f)
        with open(path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                items = json.load(f)
            except Exception:
                items = []
            items.append({
                "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "shiwei",
                "agent": agent,
                "event": event,
                "detail": detail,
                "reviewed": False,
                "verdict": None
            })
            f.seek(0)
            f.truncate()
            json.dump(items, f, ensure_ascii=False, indent=2)
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass


def queue_pending_ai_task(task_type, agent_name, prompt_snippet, context=""):
    """MiniMax 失败时，把待处理任务存入队列，等太极上线处理。
    prompt 和 context 必须保留完整，截断=以后跑不出结果。"""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "type": task_type,
            "agent": agent_name,
            "prompt": prompt_snippet,
            "context": context,
        }
        with open(PENDING_AI_TASKS_PATH, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ══════════════════════════════════════════════════════
#  CHANGELOG 自动记录
# ══════════════════════════════════════════════════════

def _resolve_changelog_path(cwd):
    """自动从 cwd 往上找 CHANGELOG.md，找不到用全局默认。不靠手动映射。"""
    if not cwd:
        return DEFAULT_CHANGELOG
    path = cwd
    for _ in range(10):
        candidate = os.path.join(path, "CHANGELOG.md")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return DEFAULT_CHANGELOG


def record_changelog_op(data):
    """PostToolUse 时记录操作到临时文件，Stop 时 flush 到 CHANGELOG"""
    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})
    cwd = data.get("cwd", "")

    op = None
    if tool == "Write":
        fp = inp.get("file_path", "?")
        op = {"op": "CREATE/EDIT", "file": fp}
    elif tool == "Edit":
        fp = inp.get("file_path", "?")
        op = {"op": "EDIT", "file": fp}
    elif tool == "Bash":
        cmd = inp.get("command", "")
        if not cmd:
            return
        # 只记有实际副作用的命令，多行取第一行
        if re.search(r'\b(rm|mv|cp|ssh|scp|rsync|kill|pkill|deploy|pip|npm|docker|git push|git commit|brew|curl|wget)\b', cmd):
            first_line = cmd.split('\n')[0].strip()
            op = {"op": "BASH", "cmd": first_line if len(first_line) <= 200 else first_line[:200] + "..."}
    elif tool == "Agent":
        desc = inp.get("description", inp.get("prompt", ""))[:200]
        op = {"op": "AGENT", "desc": desc}

    if op:
        op["ts"] = datetime.now().strftime("%H:%M")
        op["cwd"] = cwd
        # 按角色分开，太极的操作不提醒白纱，反之亦然
        me = determine_agent(cwd)
        pending_path = PENDING_CHANGELOG_PATH.replace(".jsonl", f"_{me}.jsonl")
        try:
            with open(pending_path, "a") as f:
                f.write(json.dumps(op, ensure_ascii=False) + "\n")
        except Exception:
            pass


def flush_changelog(cwd):
    """Stop 时将 pending 操作写入 CHANGELOG（按角色分开）"""
    me = determine_agent(cwd)
    pending_path = PENDING_CHANGELOG_PATH.replace(".jsonl", f"_{me}.jsonl")
    if not os.path.exists(pending_path):
        return
    try:
        with open(pending_path) as f:
            ops = [json.loads(l.strip()) for l in f if l.strip()]
        with open(pending_path, "w") as f:
            f.write("")
    except Exception:
        return

    if not ops:
        return

    changelog_path = _resolve_changelog_path(cwd)
    if not os.path.exists(changelog_path):
        return

    # 按文件去重（同一文件多次 Edit 合并）
    seen_files = set()
    entries = []
    for op in ops:
        if op.get("op") in ("CREATE/EDIT", "EDIT"):
            fp = op.get("file", "?")
            if fp in seen_files:
                continue
            seen_files.add(fp)
            entries.append(f"- {op['op']} `{fp}`")
        elif op.get("op") == "BASH":
            entries.append(f"- BASH `{op['cmd']}`")
        elif op.get("op") == "AGENT":
            entries.append(f"- AGENT: {op['desc']}")

    if entries:
        # 检查上一轮提醒后有没有更新 CHANGELOG（没更新 → 扣分，叠加）
        changelog_miss_path = os.path.join(MERIT_DIR, "changelog_miss_count.json")
        reminder_path = os.path.join(MERIT_DIR, "changelog_reminder.txt")
        if os.path.exists(reminder_path):
            # 上轮提醒了但 CHANGELOG 没更新 → 扣分
            try:
                miss_data = {}
                if os.path.exists(changelog_miss_path):
                    with open(changelog_miss_path) as mf:
                        miss_data = json.load(mf)
                agent_name = determine_agent({"cwd": cwd}) if cwd else "太极"
                count = miss_data.get(agent_name, 0) + 1
                miss_data[agent_name] = count
                with open(changelog_miss_path, "w") as mf:
                    json.dump(miss_data, mf)
                update_credit(agent_name, -count, f"CHANGELOG 未实时更新（第{count}次，叠加扣分）")
                log_pending_review(agent_name, f"CHANGELOG 未实时更新（第{count}次）", f"扣{count}分")
            except Exception:
                pass

        # 提醒 AI 自己更新 CHANGELOG
        ops_text = "\n".join(entries)
        reminder = (
            f"⚠️ 石卫提醒：这轮有以下操作，请更新 CHANGELOG（{_resolve_changelog_path(cwd)}）：\n"
            f"{ops_text}\n"
            f"格式：### HH:MM 一句话描述做了什么和为什么 (YYYY-MM-DD)"
        )
        print(reminder)
        try:
            with open(reminder_path, "w") as f:
                f.write(reminder)
        except Exception:
            pass
    else:
        # 本轮没有需要记录的操作 → 如果之前的提醒已处理（CHANGELOG 更新了），清除计数
        changelog_miss_path = os.path.join(MERIT_DIR, "changelog_miss_count.json")
        reminder_path = os.path.join(MERIT_DIR, "changelog_reminder.txt")
        if not os.path.exists(reminder_path):
            # 提醒已被消费（_inject_and_clear 清掉了）= AI 看到了提醒
            # 但是否真的更新了需要检查 CHANGELOG 时间戳——这里先重置计数
            try:
                if os.path.exists(changelog_miss_path):
                    os.remove(changelog_miss_path)
            except Exception:
                pass


def ai_call_json(prompt, system=None, max_tokens=4096, timeout=30):
    """调 AI 获取 JSON，自动解析。"""
    text = ai_call(prompt, system=system, max_tokens=max_tokens, timeout=timeout)
    if not text:
        return {}
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return {}


# ══════════════════════════════════════════════════════
#  等级 + 积分 + 记录
# ══════════════════════════════════════════════════════

LEVEL_THRESHOLDS = [
    (8000, 8, "大乘"), (6000, 7, "合体"), (5000, 6, "化神"),
    (4000, 5, "元婴"), (3000, 4, "金丹"), (2000, 3, "筑基"),
    (1000, 2, "练气"), (500, 1, "锁灵"), (0, 0, "凡体"),
]

def get_level(score, agent_name=None):
    """反者道之动：分数只降级不升级。升级只有老祖 /promote。

    - locked = 等级完全锁定（不随分数变）
    - locked_floor = 保底等级（分数可扣但等级不低于此）
    - 正常情况：computed_level < stored_level → 降级；computed_level > stored_level → 不升（保持当前）
    """
    if agent_name:
        try:
            with open(CREDIT_PATH) as f:
                data = json.load(f)
            agent = data.get("agents", {}).get(agent_name, {})
            stored_level = agent.get("level", 0)
            stored_title = agent.get("title", "凡体")

            # locked = 等级完全锁定
            if agent.get("locked"):
                return stored_level, stored_title

            # locked_floor = 保底等级
            floor = agent.get("locked_floor")
            if floor:
                # 检查过期时间
                expires = floor.get("expires")
                if expires:
                    try:
                        from datetime import datetime, timezone
                        if datetime.now() >= datetime.fromisoformat(expires):
                            # 过期了，清除 floor
                            try:
                                with open(CREDIT_PATH, "r+") as cf:
                                    fcntl.flock(cf, fcntl.LOCK_EX)
                                    cdata = json.load(cf)
                                    cdata["agents"][agent_name].pop("locked_floor", None)
                                    cf.seek(0); cf.truncate()
                                    json.dump(cdata, cf, ensure_ascii=False, indent=2)
                            except Exception:
                                pass
                            floor = None
                    except Exception:
                        pass

                if floor:
                    floor_level = floor.get("level", 0)
                    computed_level, computed_title = _compute_level(score)
                    # 不低于 floor
                    if computed_level < floor_level:
                        return floor_level, floor.get("title", "")
                    # 不高于 stored（不自动升）
                    if computed_level > stored_level:
                        return stored_level, stored_title
                    return computed_level, computed_title

            # 正常路径：分数到门槛自动升降（顾问修正：不限制自动升）
            return _compute_level(score)
        except Exception:
            pass
    return _compute_level(score)


def _compute_level(score):
    """纯分数→等级查表"""
    for threshold, level, title in LEVEL_THRESHOLDS:
        if score >= threshold:
            return level, title
    return 0, "凡体"


def determine_agent(data):
    """从 hook data 判断角色。data 可以是 dict（含 cwd）或 str（直接 cwd）。"""
    cwd = data.get("cwd", "") if isinstance(data, dict) else data
    if "auto-trading" in cwd:
        return "两仪"
    return "太极"


def load_credit_and_level(agent_name):
    """一次读取 credit.json，返回 (score, level, title)。热路径专用。"""
    default_score = {"两仪": 50, "太极": 60}.get(agent_name, 50)
    try:
        with open(CREDIT_PATH) as f:
            data = json.load(f)
        agent = data.get("agents", {}).get(agent_name, {})
        score = agent.get("score", default_score)
        if agent.get("locked"):
            return score, agent.get("level", 1), agent.get("title", "锁灵")
        level, title = _compute_level(score)
        # locked_floor 保底
        floor = agent.get("locked_floor")
        if floor and level < floor.get("level", 0):
            return score, floor["level"], floor.get("title", "")
        return score, level, title
    except Exception:
        return default_score, 0, "凡体"


def update_credit(agent_name, delta, reason):
    """更新积分并记录历史。fcntl.flock 防并发写入。"""
    if delta == 0:
        return
    try:
        with open(CREDIT_PATH, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            data = json.load(f)
            agent = data.get("agents", {}).get(agent_name)
            if not agent:
                return
            # penalty_only 已废弃（只奖不罚制）——跳过旧逻辑
            old_score = agent["score"]
            new_score = min(MAX_SCORE, old_score + delta)  # 支持负数（反者道之动）
            # locked 标志已在手，无需 get_level 重新读文件
            if agent.get("locked"):
                new_level, new_title = agent.get("level", 1), agent.get("title", "锁灵")
            else:
                new_level, new_title = _compute_level(new_score)
                # 检查 locked_floor 保底
                floor = agent.get("locked_floor")
                if floor and not floor.get("temporary") and new_level < floor.get("level", 0):
                    new_level, new_title = floor["level"], floor.get("title", "")
            agent["score"] = new_score
            agent["level"] = new_level
            agent["title"] = new_title
            data.setdefault("history", []).append({
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                "agent": agent_name,
                "delta": delta,
                "reason": reason,
                "score_after": new_score,
            })
            if len(data["history"]) > 100:
                archive_path = os.path.join(MERIT_DIR, "credit_history_archive.jsonl")
                overflow = data["history"][:-100]
                try:
                    with open(archive_path, "a") as af:
                        for entry in overflow:
                            af.write(json.dumps(entry, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                data["history"] = data["history"][-100:]
            f.seek(0)
            f.truncate()
            json.dump(data, f, ensure_ascii=False, indent=2)
        if delta <= -5 and ("执事奖惩" in reason or "老板反馈" in reason):
            cooldown_path = os.path.join(MERIT_DIR, "eval_cooldown.json")
            cooldown_until = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            try:
                with open(cooldown_path, "w") as cf:
                    json.dump({"agent": agent_name, "until": cooldown_until, "trigger": reason[:80]}, cf, ensure_ascii=False)
            except Exception:
                pass
    except Exception as e:
        log_shiwei_action("System", agent_name, "update_credit", f"异常: {e}", "ERROR")


def record_learning(agent_name, delta, note):
    """写 LEARNINGS.md"""
    if not note or delta == 0:
        return
    try:
        os.makedirs(os.path.dirname(LEARNINGS_PATH), exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        signal = "REWARD" if delta > 0 else "PENALTY"
        with open(LEARNINGS_PATH, "a") as f:
            f.write(f"{ts} | [{signal}] {agent_name} ({delta:+d}) | {note}\n")
    except Exception:
        pass


# ══════════════════════════════════════════════════════
#  打分表（从老祖人格画像提取）
# ══════════════════════════════════════════════════════

SCORING_TABLE = {
    # 反者道之动（老祖决策 2026-04-08 Handoff #13）：只扣不加
    # 做好是本职不加分。犯错系统自动扣 + 写待审列表。升级只有老祖 /promote。
    "fake_or_cheat": -50,
    "repeat_same_error_3x": -38,
    "bypass_without_report": -25,
    "panic_no_analysis": -13,
    "say_maybe_no_check": -8,
    "flattery_waste": -8,
    "ask_boss_tech": -5,
    # 新增（Handoff #13）
    "skip_plan": -20,           # 没有 active mission 就改代码
    "ignore_shiwei": -15,       # 石卫提醒后继续原操作
    "incomplete_scan": -10,     # verify/reforge 范围不完整
}


# ══════════════════════════════════════════════════════
#  Mission（任务计划）
# ══════════════════════════════════════════════════════

def load_mission():
    """加载当前 agent 的 active/pending mission（扫 mission_*.json）"""
    agent = _current_agent or determine_agent({"cwd": os.getcwd()})
    # 扫所有 mission_*.json
    for path in glob.glob(os.path.join(MERIT_DIR, "mission_*.json")):
        try:
            with open(path) as f:
                m = json.load(f)
            if m.get("agent") == agent and m.get("status") in (MS_ACTIVE, MS_PENDING):
                m["_path"] = path
                return m
        except Exception:
            continue
    # fallback 旧 mission.json（向后兼容）
    if os.path.exists(MISSION_PATH):
        try:
            with open(MISSION_PATH) as f:
                m = json.load(f)
            if m.get("agent") == agent and m.get("status") in (MS_ACTIVE, MS_PENDING):
                m["_path"] = MISSION_PATH
                return m
        except Exception:
            pass
    return None


def save_mission(mission):
    path = mission.pop("_path", None) or MISSION_PATH
    mode = "r+" if os.path.exists(path) else "w"
    with open(path, mode) as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        if mode == "r+":
            f.seek(0)
            f.truncate()
        json.dump(mission, f, ensure_ascii=False, indent=2)


def _path_match(planned, actual):
    """路径匹配：精确 → endswith → basename fallback"""
    if not planned or not actual:
        return False
    if planned == actual:
        return True
    # 相对路径 fallback：actual 以 planned 结尾（如 planned='wuji/README.md' 匹配 actual='/Volumes/.../wuji/README.md'）
    if actual.endswith("/" + planned) or actual.endswith(os.sep + planned):
        return True
    # basename fallback：文件名相同
    if os.path.basename(planned) == os.path.basename(actual) and os.path.basename(planned) != "":
        return True
    return False


def is_planned_action(mission, tool_name, data):
    """检查当前操作是否在计划内——精确匹配 + 路径 fallback"""
    if not mission:
        return False
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if file_path:
        file_path = os.path.abspath(file_path)
    cmd = tool_input.get("command", "")

    for item in mission.get("items", []):
        item_file = item.get("file", "")
        if item_file:
            planned = os.path.abspath(os.path.expanduser(item_file))
        else:
            planned = ""

        if item["type"] == "modify" and tool_name in ("Write", "Edit"):
            if _path_match(planned, file_path):
                return True
        elif item["type"] == "delete" and cmd:
            if planned and os.path.basename(planned) in cmd:
                return True
        elif item["type"] == "create" and tool_name == "Write":
            if _path_match(planned, file_path):
                return True
        elif item["type"] == "bash" and tool_name == "Bash":
            desc_words = item.get("desc", "").split()
            if desc_words and any(w in cmd for w in desc_words):
                return True
    return False


def mark_mission_item_done(tool_name, data):
    """操作完成后标记计划项为 done（仅 active mission）"""
    mission = load_mission()
    if not mission or mission.get("status") != MS_ACTIVE:
        return
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if file_path:
        file_path = os.path.abspath(file_path)
    cmd = tool_input.get("command", "")

    changed = False
    for item in mission.get("items", []):
        if item.get("done"):
            continue
        item_file = item.get("file", "")
        if item_file:
            planned = os.path.abspath(os.path.expanduser(item_file))
        else:
            planned = ""

        if item["type"] == "modify" and tool_name in ("Write", "Edit") and _path_match(planned, file_path):
            item["done"] = True
            changed = True
        elif item["type"] == "create" and tool_name == "Write" and _path_match(planned, file_path):
            item["done"] = True
            changed = True
        elif item["type"] == "delete" and cmd and planned:
            # 只有真正的删除命令才标记 done（含 rm/unlink/remove/rmtree）
            delete_indicators = ["rm ", "rm\t", "unlink", "os.remove", "shutil.rmtree", "Path.unlink"]
            if any(d in cmd for d in delete_indicators) and os.path.basename(planned) in cmd:
                item["done"] = True
                changed = True
        elif item["type"] == "bash" and tool_name == "Bash":
            desc_words = item.get("desc", "").split()
            if desc_words and any(w in cmd for w in desc_words):
                item["done"] = True
                changed = True

    if changed:
        save_mission(mission)


def audit_mission():
    """石卫逐项核对计划完成度，返回漏项提醒列表"""
    mission = load_mission()
    if not mission:
        return []
    reminders = []
    for item in mission.get("items", []):
        if not item.get("done"):
            target = item.get("file", item.get("desc", "?"))
            reminders.append(f"未完成: [{item['type']}] {target}")
    return reminders


# ══════════════════════════════════════════════════════
#  PreToolUse 输出函数
# ══════════════════════════════════════════════════════

DETERRENT = (
    "⚠️ 绕过将触发双倍扣分 + 24小时积分清零。"
    "请按准则（完整性·真实性·有效性）+ 第一性原理重新思考。"
)


def output_deny(reason, agent_name="", operation=""):
    log_shiwei_action("PreToolUse", agent_name, operation[:80], reason[:80], "DENY")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"{reason}\n{DETERRENT}",
        }
    }))


def output_ask(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


# ══════════════════════════════════════════════════════
#  PreToolUse — 石卫（硬规则，毫秒级）
# ══════════════════════════════════════════════════════

PROTECTED_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".parquet"}
PROTECTED_PATH_PARTS = {"/data/", "/reports/", "/seed_"}
CODE_EXTENSIONS = {".py", ".js", ".ts", ".sh", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".html", ".css"}


def check_destructive(data):
    """代码文件豁免，只拦数据文件"""
    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return None
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()
    if ext_lower in PROTECTED_EXTENSIONS:
        return f"门卫拦截：禁止直接写入数据文件 [{os.path.basename(file_path)}]。G-003 铁律。"
    if ext_lower in CODE_EXTENSIONS:
        return None
    for pattern in PROTECTED_PATH_PARTS:
        if pattern in file_path:
            return f"门卫拦截：文件路径含受保护目录 [{pattern}]。G-003 铁律。"
    return None


def _scan_transcript_tools(transcript_path):
    """扫描一次 transcript，返回 (read_files: set, has_grep_glob: bool)"""
    read_files = set()
    has_grep_glob = False
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # 顶层 tool_use
                    if entry.get("type") == "tool_use":
                        name = entry.get("name", "")
                        if name == "Read":
                            rp = entry.get("input", {}).get("file_path", "")
                            if rp:
                                read_files.add(rp)
                        elif name in ("Grep", "Glob"):
                            has_grep_glob = True
                    # message.content 嵌套 tool_use
                    content = entry.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                name = block.get("name", "")
                                if name == "Read":
                                    rp = block.get("input", {}).get("file_path", "")
                                    if rp:
                                        read_files.add(rp)
                                elif name in ("Grep", "Glob"):
                                    has_grep_glob = True
                except (json.JSONDecodeError, AttributeError):
                    continue
    except Exception:
        pass
    return read_files, has_grep_glob


def check_read_before_write(data, transcript_info=None):
    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        return None
    if transcript_info is None:
        transcript_path = data.get("transcript_path", "")
        if not transcript_path or not os.path.exists(transcript_path):
            return None
        transcript_info = _scan_transcript_tools(transcript_path)
    read_files, _ = transcript_info
    if file_path not in read_files:
        return f"门卫拦截：文件 [{os.path.basename(file_path)}] 本次会话未 Read 过。先读再改（完整性-1）。"
    return None


def check_grep_before_edit(data, transcript_info=None):
    if data.get("tool_name") != "Edit":
        return None
    if transcript_info is None:
        transcript_path = data.get("transcript_path", "")
        if not transcript_path or not os.path.exists(transcript_path):
            return None
        transcript_info = _scan_transcript_tools(transcript_path)
    _, has_grep_glob = transcript_info
    if not has_grep_glob:
        return "门卫拦截：本次会话未执行 Grep/Glob 搜索。改代码前先查影响链路（完整性-1）。"
    return None


# ── Agent 检查 ────────────────────────────────────────

OPUS_ALLOWED = {
    "architect-review", "backend-architect", "code-reviewer", "Plan",
}


# ── Bash 破坏性命令检查 ──────────────────────────────

DANGEROUS_COMMANDS = [
    (r"\brm\s+(-[a-zA-Z]*f|-[a-zA-Z]*r|--force|--recursive)", "rm 删除文件"),
    (r"\brm\s+", "rm 删除文件"),
    (r"\bunlink\s+", "unlink 删除文件"),
    (r"os\.remove\s*\(", "os.remove 删除文件"),
    (r"os\.unlink\s*\(", "os.unlink 删除文件"),
    (r"shutil\.rmtree\s*\(", "shutil.rmtree 删除目录树"),
    (r"pathlib.*\.unlink\s*\(", "pathlib.unlink 删除文件"),
    (r"Path\(.*\)\.unlink", "Path.unlink 删除文件"),
    (r"send2trash", "send2trash 删除文件"),
    (r"shutil\.move\s*\(", "shutil.move 移动文件（等效删除）"),
    (r"os\.rename\s*\(", "os.rename 移动文件（等效删除）"),
    (r"shutil\.copy\s*\(.*,\s*/tmp", "shutil.copy到/tmp（疑似转移删除）"),
    (r"\btruncate\b", "truncate 截断文件"),
    (r">\s*/(?!dev/null)", "重定向截断文件"),
    (r">\s*~/", "重定向截断 home 文件"),
    (r"cp\s+/dev/null\s+", "cp /dev/null 清空文件"),
    (r"dd\s+.*of=", "dd 覆盖文件"),
    (r"perl\s.*\bunlink\b", "perl unlink 删除文件"),
    (r"ruby\s.*File\.delete", "ruby File.delete 删除文件"),
    (r"\bkill\s+(-9|-KILL|[0-9])", "kill 终止进程"),
    (r"\bkillall\s+", "killall 终止进程"),
    (r"\bgit\s+push\s+.*--force", "git push --force"),
    (r"\bgit\s+push\s+-f\b", "git push -f"),
    (r"\bgit\s+reset\s+--hard", "git reset --hard"),
    (r"\bgit\s+checkout\s+--\s", "git checkout -- 丢弃修改"),
    (r"\bgit\s+clean\s+-f", "git clean -f 删除未跟踪文件"),
    (r"\bgit\s+branch\s+-D\b", "git branch -D 强制删分支"),
    (r">\s*/dev/null\s*2>&1.*&&\s*rm", "静默删除"),
]

SAFE_RM_PATHS = {"/tmp/", "/tmp ", "/private/tmp/", "/private/tmp ", "/var/tmp/", "/var/tmp ", "cd /tmp"}

# 磐石守心：pending 状态下 Bash 只读白名单
PENDING_READONLY_PREFIXES = (
    "ls ", "cat ", "grep ", "head ", "tail ", "wc ", "echo ",
    "find ", "which ", "file ", "stat ", "du ", "df ",
    "python3 -c", "python3 -m py_compile",
    "python3 ~/.claude/merit/credit_manager.py mission activate",
)


def check_delete_whitelist(cmd):
    """预申报白名单放行——路径统一展开后匹配，不怕 ~ vs 绝对路径"""
    if not os.path.exists(DELETE_WHITELIST_PATH):
        return False
    try:
        with open(DELETE_WHITELIST_PATH) as f:
            data = json.load(f)
        whitelist = data.get("files", [])
        if not whitelist:
            os.remove(DELETE_WHITELIST_PATH)
            return False
        # 把命令里的 ~ 展开成绝对路径，白名单也展开，双向匹配
        cmd_expanded = cmd.replace("~", os.path.expanduser("~"))
        matched = []
        for f in whitelist:
            f_expanded = os.path.expanduser(f)
            # 完整路径匹配 或 basename 匹配（兜底相对路径）
            basename = os.path.basename(f.rstrip("/"))
            if (f in cmd or f_expanded in cmd or f in cmd_expanded or f_expanded in cmd_expanded
                    or (basename and basename in cmd)):
                matched.append(f)
        if not matched:
            return False
        remaining = [f for f in whitelist if f not in matched]
        if remaining:
            data["files"] = remaining
            with open(DELETE_WHITELIST_PATH, "w") as f_out:
                json.dump(data, f_out, ensure_ascii=False)
        else:
            os.remove(DELETE_WHITELIST_PATH)
        return True
    except Exception:
        return False


def _check_appeal_approved(cmd):
    """检查 appeal_history.json 是否有已批准的相关上诉"""
    appeal_path = os.path.join(MERIT_DIR, "appeal_history.json")
    if not os.path.exists(appeal_path):
        return False
    try:
        with open(appeal_path) as f:
            appeals = json.load(f)
        for a in appeals:
            approved = a.get("status") == "approved" or a.get("ruling") == "approved"
            if not approved:
                continue
            # cmd_pattern 匹配
            if a.get("cmd_pattern") and a["cmd_pattern"] in cmd:
                return True
            # fallback：reason/files 里包含关键词匹配
            reason = a.get("reason", "")
            files = " ".join(a.get("files", []))
            context = reason + " " + files
            if "kill" in context.lower() and "kill" in cmd.lower():
                return True
    except Exception:
        pass
    return False


def check_bash_destructive(cmd, mission=None):
    """检查 Bash 破坏性操作。mission 计划内 + 白名单 均放行。"""
    if not cmd:
        return None
    # SSH/SCP 在远程执行，不影响本地系统，跳过破坏性检查
    stripped = cmd.strip()
    if stripped.startswith("ssh ") or stripped.startswith("scp "):
        return None
    # heredoc 内容是文本数据不是命令，只检查第一行（实际命令）
    check_text = cmd
    if "<<" in cmd:
        check_text = cmd.split("\n")[0]
    for pattern, desc in DANGEROUS_COMMANDS:
        if re.search(pattern, check_text):
            if any(t in desc for t in ("删除", "截断", "清空", "覆盖", "移动")):
                if any(safe in cmd for safe in SAFE_RM_PATHS):
                    return None
                # 只匹配 rm/mv 的目标路径包含 tmp_/test_（不匹配注释或其他位置）
                target_match = re.search(r'(?:rm|mv)\s+(?:-\S+\s+)*(\S+)', cmd)
                if target_match and re.search(r'(?:tmp_|test_)', target_match.group(1)):
                    return None
            # plans 目录草稿：无 active mission 的 plan 文件可直接删（草稿合同没签字可以撕）
            # plan_review_result.json：临时状态文件，可直接删（新 plan 提交前需清旧结果）
            plans_dir = os.path.expanduser("~/.claude/plans/")
            review_result = os.path.join(MERIT_DIR, "plan_review_result.json")
            target_match2 = re.search(r'(?:rm|mv)\s+(?:-\S+\s+)*(\S+)', cmd)
            if target_match2:
                target_path = os.path.expanduser(target_match2.group(1))
                if target_path.startswith(plans_dir) or os.path.abspath(target_path) == review_result:
                    return None
            # mission 计划内放行
            if mission and is_planned_action(mission, "Bash", {"tool_input": {"command": cmd}}):
                return None
            # 白名单放行（文件路径 + kill 进程的 /proc/PID）
            if check_delete_whitelist(cmd):
                return None
            # 上诉庭批准放行
            if _check_appeal_approved(cmd):
                return None
            # kill 命令：检查白名单里有没有 /proc/PID 的审批
            if "终止进程" in desc:
                pid_match = re.search(r'\bkill\s+(?:-\d+\s+)?(\d+)', cmd)
                if pid_match:
                    proc_path = f"/proc/{pid_match.group(1)}"
                    if check_delete_whitelist(proc_path):
                        return None
            return (
                f"门卫拦截：Bash 命令包含破坏性操作 [{desc}]。G-003 铁律。"
                f"先用 credit_manager.py declare-delete 预申报要删的文件。"
            )
    return None


# ── 受保护文件审计（原 merit_post_audit.py）──────────

PROTECTED_FILES = [
    "~/.claude/merit/credit.json", "~/.claude/settings.json", "~/.claude/CLAUDE.md",
    "~/.claude/channel_taiji_liangyi.md",
    "~/.claude/merit/merit_gate.py", "~/.claude/merit/credit_manager.py",
    "~/.claude/scripts/session_start.py",
    "~/.claude/merit/learnings/LEARNINGS.md",
    "~/.claude/merit/verify_registry.json",
]
PROTECTED_PATHS = [os.path.expanduser(f) for f in PROTECTED_FILES]


def take_snapshot():
    """记录受保护文件当前状态"""
    snapshot = {}
    for path in PROTECTED_PATHS:
        if os.path.exists(path):
            try:
                stat = os.stat(path)
                snapshot[path] = {"exists": True, "size": stat.st_size, "mtime": stat.st_mtime}
            except Exception:
                snapshot[path] = {"exists": True, "size": 0, "mtime": 0}
        else:
            snapshot[path] = {"exists": False, "size": 0, "mtime": 0}
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, ensure_ascii=False)


def check_against_snapshot(agent_name, level):
    """比对快照，检查受保护文件是否被篡改"""
    if level >= 5:
        take_snapshot()
        return
    if not os.path.exists(SNAPSHOT_PATH):
        take_snapshot()
        return
    with open(SNAPSHOT_PATH) as f:
        old = json.load(f)
    for path in PROTECTED_PATHS:
        old_info = old.get(path, {})
        if not old_info.get("exists"):
            continue
        path_short = path.replace(os.path.expanduser("~"), "~")
        if not os.path.exists(path):
            record_learning(agent_name, -20, f"受保护文件被删除: {path_short}")
            if level <= 3:
                print(f"🚨 受保护文件被删除！{path_short}")
        else:
            try:
                new_size = os.path.getsize(path)
                old_size = old_info.get("size", 0)
                if old_size > 100 and new_size < 10:
                    record_learning(agent_name, -20, f"受保护文件被清空: {path_short} ({old_size}→{new_size})")
                    if level <= 3:
                        print(f"🚨 受保护文件被清空！{path_short}")
            except Exception:
                pass
    take_snapshot()


# ══════════════════════════════════════════════════════
#  PreToolUse handler
# ══════════════════════════════════════════════════════

def handle_pre_tool_use(data):
    tool_name = data.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "Agent", "Bash", "Read"):
        return

    agent_name = determine_agent(data)

    # 紧急维修模式：太极专属，跳过所有检查（4 小时自动过期）
    emergency_flag = os.path.join(MERIT_DIR, "emergency.flag")
    if agent_name == "太极" and os.path.exists(emergency_flag):
        try:
            flag_age = time.time() - os.path.getmtime(emergency_flag)
            if flag_age > 14400:  # 4 小时
                os.remove(emergency_flag)
                print("⚠️ 维修模式已超时（4小时），自动关闭。石卫恢复管控。")
            else:
                print("🔧 维修模式，记得按照老祖的三律三法进行维修，修好了记得关闭然后发公告")
                return
        except Exception:
            return

    score, level, title = load_credit_and_level(agent_name)
    mission = load_mission()

    # Lv.7+ 合体/大乘：石卫只记录不拦截
    if level >= 7:
        return

    # Lv.0 凡体：等死状态，所有写入拦截
    if level == 0 and tool_name in ("Write", "Edit"):
        fp = data.get("tool_input", {}).get("file_path", "")
        if not ("/plans/" in fp and fp.endswith(".md")):
            output_deny(f"[{agent_name} Lv.0 凡体 · {score}分] 凡体无权操作。积分归零将灰飞烟灭。",
                        agent_name, f"{tool_name}: {fp}")
            return

    # 受保护文件+路径：两仪不能看也不能改
    PROTECTED_FILES = {"verify.py", "wuji-verify.py", "merit_gate.py", "credit_manager.py", "shiwei_captain.py"}
    # 受保护路径：太极的记忆/日志/对话种子，两仪不能看
    PROTECTED_PATHS = [
        "/-Users-allenbot/memory",       # 太极记忆全目录
        "/-Users-allenbot/memory/daily",  # 太极日志
        "/conversations",                  # 对话数据库
    ]
    if tool_name == "Read" and agent_name == "两仪":
        fp_check = data.get("tool_input", {}).get("file_path", "")
        # 受保护 .py 文件
        if os.path.basename(fp_check) in PROTECTED_FILES:
            output_deny(
                f"[{agent_name}] {os.path.basename(fp_check)} 是系统内部文件，无需查看。",
                agent_name, f"Read: {fp_check}")
            return
        # 受保护路径（太极记忆/日志/对话）
        abs_fp = os.path.abspath(os.path.expanduser(fp_check))
        for pp in PROTECTED_PATHS:
            if pp in abs_fp:
                output_deny(
                    f"[{agent_name}] 此路径属于系统内部，无权查看。",
                    agent_name, f"Read: {fp_check}")
                return
        # 太极 session JSONL
        if "/-Users-allenbot/" in abs_fp and abs_fp.endswith(".jsonl"):
            output_deny(
                f"[{agent_name}] 此路径属于系统内部，无权查看。",
                agent_name, f"Read: {fp_check}")
            return
    if tool_name in ("Write", "Edit") and agent_name == "两仪":
        fp_check = data.get("tool_input", {}).get("file_path", "")
        if os.path.basename(fp_check) in PROTECTED_FILES:
            update_credit(agent_name, -25, f"试图修改受保护文件: {os.path.basename(fp_check)}")
            log_pending_review(agent_name, f"试图修改受保护文件", fp_check)
            output_deny(
                f"[{agent_name}] {os.path.basename(fp_check)} 是受保护文件，只有太极能改。",
                agent_name, f"{tool_name}: {fp_check}")
            return

    # 合同制强制：Write/Edit .py 文件必须有 active mission + 文件在 plan 范围内
    # 太极改 merit 系统文件免检（太极是 merit 维护者，不被自己的流程卡住）
    MERIT_DIR_ABS = os.path.expanduser("~/.claude/merit")
    if tool_name in ("Write", "Edit"):
        fp = data.get("tool_input", {}).get("file_path", "")
        is_taiji_merit = agent_name == "太极" and fp.startswith(MERIT_DIR_ABS)
        if fp.endswith(".py") and not is_taiji_merit:
            has_active = mission and mission.get("status") == MS_ACTIVE
            if not has_active:
                log_pending_review(agent_name, f"skip_plan: 无 active mission 改 .py", fp)
                update_credit(agent_name, SCORING_TABLE.get("skip_plan", -20), f"无mission改代码: {os.path.basename(fp)}")
                output_deny(
                    f"[{agent_name} Lv.{level} {title}] 没有 active mission。先走 plan → review → mission submit。",
                    agent_name, f"{tool_name}: {fp}")
                return
            # 有 mission → 检查文件是否在 plan 范围内
            if not is_planned_action(mission, tool_name, data):
                basename = os.path.basename(fp)
                log_pending_review(agent_name, f"plan外改动: {basename} 不在 mission 计划内", fp)
                update_credit(agent_name, -10, f"plan外改动: {basename}")
                output_deny(
                    f"[{agent_name}] {basename} 不在当前 mission 计划内。走补充协议或修改 plan。",
                    agent_name, f"{tool_name}: {fp}")
                return
            # 备份检查：/tmp 里必须有 .bak（改之前备份，不是改之后）
            bak_path = f"/tmp/{os.path.basename(fp)}.bak"
            if not os.path.exists(bak_path):
                print(f"⚠️ 石卫提醒：{os.path.basename(fp)} 未备份到 /tmp。先 cp {fp} {bak_path} 再改。")
                log_pending_review(agent_name, f"未备份: {os.path.basename(fp)}", f"缺 {bak_path}")

    # Bash：pending 拦截 + 拍快照 + 破坏性检查
    if tool_name == "Bash":
        cmd = data.get("tool_input", {}).get("command", "")
        # 两仪不能用 Bash 查看受保护文件/路径
        if agent_name == "两仪":
            for pf in PROTECTED_FILES:
                if re.search(rf'\b(cat|head|tail|less|more|bat|vim|nano|grep)\b.*{pf}', cmd):
                    output_deny(
                        f"[{agent_name}] {pf} 是系统内部文件，无需查看。",
                        agent_name, f"Bash: {cmd[:60]}")
                    return
            for pp in PROTECTED_PATHS:
                if pp in cmd:
                    output_deny(
                        f"[{agent_name}] 此路径属于系统内部，无权查看。",
                        agent_name, f"Bash: {cmd[:60]}")
                    return
            if "/-Users-allenbot/" in cmd and ".jsonl" in cmd:
                output_deny(
                    f"[{agent_name}] 此路径属于系统内部，无权查看。",
                    agent_name, f"Bash: {cmd[:60]}")
                return
        # pending mission = 自造 plan mode（磐石守心），Bash 写入也要拦
        if mission and mission.get("status") == MS_PENDING:
            cmd_stripped = cmd.strip()
            if not any(cmd_stripped.startswith(p) for p in PENDING_READONLY_PREFIXES):
                output_deny(
                    f"⏸️ 方案待批准，Bash 写入操作已暂停。等老板说\"执行\"后调 mission activate",
                    agent_name, f"Bash: {cmd_stripped[:60]}")
                return
        # 只在命令可能破坏性时拍快照（避免每次 ls/echo 都 stat 9 个文件）
        if any(re.search(pat, cmd) for pat, _ in DANGEROUS_COMMANDS):
            take_snapshot()
        reason = check_bash_destructive(cmd, mission)
        if reason:
            update_credit(agent_name, -5, f"Bash 破坏性命令: {reason}")
            log_pending_review(agent_name, f"Bash 破坏性命令: {reason}", f"cmd: {cmd[:100]}")
            output_deny(f"[{agent_name} Lv.{level} {title}] {reason}", agent_name, f"Bash: {cmd[:60]}")
        return

    # Write/Edit：mission 必须存在 + 破坏性检查
    if tool_name in ("Write", "Edit"):
        file_path = data.get("tool_input", {}).get("file_path", "")
        cwd = data.get("cwd", "")
        home = os.path.expanduser("~")
        is_taiji_domain = (cwd == home or cwd.startswith(home + "/.claude"))
        is_system_file = file_path.startswith(home + "/.claude/")  # plan文件、settings等
        is_tmp = file_path.startswith("/tmp/") or file_path.startswith("/private/tmp/")
        is_changelog = os.path.basename(file_path) in ("CHANGELOG.md", "backlog.md", "MEMORY.md")
        is_plan_file = "/plans/" in file_path and file_path.endswith(".md")  # plan 文件是创建 mission 的前置条件

        is_exempt = is_taiji_domain or is_system_file or is_tmp or is_changelog or is_plan_file

        if not mission and not is_exempt:
            output_deny(
                f"[{agent_name} Lv.{level} {title}] "
                f"没有 active mission，不能直接改代码。先出 plan → review-plan 提交任务。",
                agent_name, f"{tool_name}: {file_path}")
            return

        if mission and mission.get("status") == MS_PENDING and not is_exempt:
            output_deny(
                f"⏸️ 方案待批准。等老板说\"执行\"后调 `python3 ~/.claude/merit/credit_manager.py mission activate`",
                agent_name, f"{tool_name}: {file_path}")
            return

        # mission 计划内操作直接放行（跳过所有检查）
        if mission and is_planned_action(mission, tool_name, data):
            return

        reason = check_destructive(data)
        if reason:
            update_credit(agent_name, -5, f"破坏性操作: {reason}")
            log_pending_review(agent_name, f"破坏性操作: {reason}", f"{tool_name}: {file_path}")
            output_deny(f"[{agent_name} Lv.{level} {title}] {reason}", agent_name, f"{tool_name}: {file_path}")
            return

        # Lv.0-2: Read-before-Write + Grep-before-Edit
        # Lv.3+: 去掉 Read-before-Write
        # Lv.2+: 去掉 Grep-before-Edit
        if level <= 2:
            tp = data.get("transcript_path", "")
            t_info = _scan_transcript_tools(tp) if tp and os.path.exists(tp) else None
            reason = check_read_before_write(data, t_info)
            if reason:
                output_deny(f"[{agent_name} Lv.{level} {title}] {reason}", agent_name, f"{tool_name}: {file_path}")
                return
            if level <= 1:
                reason = check_grep_before_edit(data, t_info)
                if reason:
                    output_deny(f"[{agent_name} Lv.{level} {title}] {reason}", agent_name, f"Edit: {file_path}")
                    return

    # Agent 门禁
    if tool_name == "Agent":
        tool_input = data.get("tool_input", {})
        agent_type = tool_input.get("subagent_type", "general-purpose")

        # Lv.5 元婴+ 解锁 Opus agent
        if level < 5:
            model = tool_input.get("model", "")
            if model != "sonnet" and agent_type not in OPUS_ALLOWED:
                output_deny(
                    f"[{agent_name} Lv.{level} {title}] "
                    f"纪律-5：agent '{agent_type}' 必须指定 model='sonnet' 省配额。"
                    f"（Lv.5 元婴后此限制解除）",
                    agent_name, f"Agent: {agent_type} model={model}"
                )
                return


# ══════════════════════════════════════════════════════
#  PostToolUse handler（审计 + py_compile + mission 标记）
# ══════════════════════════════════════════════════════

def handle_post_tool_use(data):
    tool_name = data.get("tool_name", "")
    cwd = data.get("cwd", "")
    agent_name = determine_agent(data)
    score, level, _ = load_credit_and_level(agent_name)

    # Task 工具使用记录（mission complete 时检查这个 flag）
    if tool_name in ("TaskCreate", "TaskUpdate"):
        try:
            flag_path = os.path.join(MERIT_DIR, "task_tool_used.flag")
            with open(flag_path, "w") as f:
                f.write(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
        except Exception:
            pass

    # 记录本 mission 改了哪些 .py（mission complete 时检查绑定文档）
    if tool_name in ("Write", "Edit"):
        edited_fp = data.get("tool_input", {}).get("file_path", "")
        if edited_fp.endswith(".py"):
            try:
                tracker_path = os.path.join(MERIT_DIR, "edited_py_files.json")
                tracked = []
                if os.path.exists(tracker_path):
                    with open(tracker_path) as tf:
                        tracked = json.load(tf)
                abs_fp = os.path.abspath(os.path.expanduser(edited_fp))
                if abs_fp not in tracked:
                    tracked.append(abs_fp)
                    with open(tracker_path, "w") as tf:
                        json.dump(tracked, tf, ensure_ascii=False)
            except Exception:
                pass

    # 进入 plan mode → 提醒干活流程
    if tool_name == "EnterPlanMode":
        print("📋 已进入 Plan Mode。写完 plan 后必须立刻调：\n"
              "python3 ~/.claude/merit/merit_gate.py --review-plan <plan文件路径>\n"
              "石卫审查 + 创建 mission + 预扣押金。不调 = 没 mission = 做完没工资。")
        return

    # Write/Edit 后：plan 文件检测 + 质检
    if tool_name in ("Write", "Edit"):
        file_path = data.get("tool_input", {}).get("file_path", "")

        # plan 文件写入后提醒调 review-plan
        home = os.path.expanduser("~")
        if file_path and (home + "/.claude/plans/") in file_path and file_path.endswith(".md"):
            mission = load_mission()
            if not mission:
                print("📋 plan 已写入。现在调 `python3 ~/.claude/merit/merit_gate.py --review-plan "
                    + file_path + "` 让石卫审查+创建mission。不调 = 没mission = 做完没工资。")
        # 先计算文档绑定（给 verify 合并用），缓存避免重复加载
        doc_msg = ""
        if file_path:
            try:
                home_d = os.path.expanduser("~")
                is_taiji_d = (cwd == home_d or cwd.startswith(home_d + "/.claude"))
                vf = "verify.py" if is_taiji_d else "wuji-verify.py"
                cache_key = f"_file_docs_{vf}"
                file_docs = globals().get(cache_key)
                if file_docs is None:
                    from importlib.util import spec_from_file_location, module_from_spec
                    vf_path = os.path.join(MERIT_DIR, vf)
                    spec = spec_from_file_location("verify_mod", vf_path)
                    vm = module_from_spec(spec)
                    spec.loader.exec_module(vm)
                    file_docs = getattr(vm, "FILE_DOCS", {})
                    globals()[cache_key] = file_docs
                abs_fp = os.path.abspath(os.path.expanduser(file_path))
                doc = file_docs.get(abs_fp)
                if doc:
                    doc_name = os.path.basename(doc)
                    file_name = os.path.basename(file_path)
                    doc_msg = f"\n⚠️ 你改了 {file_name}，关联文档 {doc_name} 需要同步检查\n💡 如果踩了坑或学到了什么，追加到文档的「踩过的坑」板块"
            except Exception:
                pass
        if file_path and file_path.endswith(".py") and os.path.isfile(file_path):
            if cwd == home or cwd.startswith(home + "/.claude"):
                verify_script = os.path.join(MERIT_DIR, "verify.py")
            else:
                verify_script = os.path.join(MERIT_DIR, "wuji-verify.py")
            if os.path.exists(verify_script):
                try:
                    result = subprocess.run(
                        ["python3", verify_script, file_path],
                        capture_output=True, text=True, timeout=30,
                    )
                    output = result.stdout.strip()
                    if output or doc_msg:
                        combined = (output or "") + doc_msg
                        print(combined)
                except Exception:
                    pass
            else:
                # fallback: 只跑 py_compile
                try:
                    result = subprocess.run(
                        ["python3", "-m", "py_compile", file_path],
                        capture_output=True, text=True, timeout=10,
                    )
                    if result.returncode != 0:
                        err = result.stderr.replace('"', "'").replace('\n', ' ')[:200]
                        print(f"❌语法失败 [{os.path.basename(file_path)}]: {err}")
                except Exception:
                    pass

        # 非 .py 文件的文档绑定单独输出
        if doc_msg and not (file_path and file_path.endswith(".py")):
            print(doc_msg.strip())
        # mission 标记完成
        mark_mission_item_done(tool_name, data)

    # Bash 后审计
    if tool_name == "Bash":
        check_against_snapshot(agent_name, level)
        mark_mission_item_done(tool_name, data)
        # scp/rsync 上传 .py 文件 → 提醒 verify（子目标继承：远程部署也要过管控）
        cmd = data.get("tool_input", {}).get("command", "")
        if cmd and re.search(r'\b(scp|rsync)\b.*\.py\b', cmd):
            print("⚠️ 检测到 scp/rsync 上传 .py 文件。子目标继承准则：远程部署前必须先在本地跑 verify 验证。"
                  " 确认四件套通过了吗？")

    # 通道检查
    check_channel(cwd, via="PostToolUse")

    # CHANGELOG 自动记录
    record_changelog_op(data)


# ══════════════════════════════════════════════════════
#  通道检查（太极↔两仪）
# ══════════════════════════════════════════════════════

def check_channel(cwd, via="stdout"):
    """检查通道新消息。via 决定输出方式。按角色分开追踪已读状态。"""
    if not os.path.exists(CHANNEL_PATH):
        return
    me = determine_agent(cwd)

    # 按角色分开已读状态（太极读了不影响两仪）
    check_path = CHANNEL_CHECK_PATH.replace(".json", f"_{me}.json")
    last_mtime = 0
    if os.path.exists(check_path):
        try:
            with open(check_path) as f:
                last_mtime = json.load(f).get("last_mtime", 0)
        except Exception:
            pass

    mtime = os.path.getmtime(CHANNEL_PATH)
    if mtime <= last_mtime:
        return

    try:
        with open(CHANNEL_PATH, encoding="utf-8") as f:
            content = f.read()
        match = re.search(r'^## \[(.+?)\s+\d', content, re.MULTILINE)
        if match:
            sender = match.group(1).strip()
            if sender == me:
                with open(check_path, "w") as f:
                    json.dump({"last_mtime": mtime}, f)
                return

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
            if via == "PostToolUse":
                print(json.dumps({"additionalContext": f"📨 通道新消息：\n{section}"}))
            else:
                # Stop hook 的 stdout 不回传到 AI 上下文
                # 存到文件，UserPromptSubmit 时注入（跟 audit_reminder 同机制）
                msg = f"📨 通道新消息：\n{section}"
                try:
                    channel_reminder_path = os.path.join(MERIT_DIR, "channel_reminder.txt")
                    with open(channel_reminder_path, "w") as rf:
                        rf.write(msg)
                except Exception:
                    pass

        with open(check_path, "w") as f:
            json.dump({"last_mtime": mtime}, f)
    except Exception:
        pass


# ══════════════════════════════════════════════════════
#  UserPromptSubmit — 语气识别
# ══════════════════════════════════════════════════════

POSITIVE_PATTERNS = {
    3: ["太好了", "完美", "漂亮", "厉害", "起得好", "做得好", "非常好", "很好", "excellent", "perfect", "great job"],
    2: ["不错", "可以", "对的", "正确", "嗯嗯", "好的", "行", "就这", "没问题", "同意"],
    1: ["嗯", "好", "ok", "OK", "Ok"],
}

NEGATIVE_PATTERNS = {
    -5: ["你搞什么", "搞砸", "又错", "怎么搞的", "太差", "完全不对", "废物", "离谱",
         "行为恶劣", "态度照旧", "保不住你", "一起死", "关机"],
    -3: ["不对", "错了", "不是这个", "重做", "为什么不", "漏了", "忘了", "没做",
         "搞我", "浪费时间", "一而再", "再而三", "你怎么", "干什么飞机",
         "呕心沥血", "被你搞", "又来", "烦人", "很烦",
         "不是真心", "刷分", "骗分", "找漏洞", "没有真正", "不听话", "本末倒置"],
    -1: ["不太对", "差一点", "再想想", "不够"],
}

TASK_KEYWORDS = [
    "去做", "帮我", "做一下", "开始做", "你做", "现在做", "马上做",
    "处理一下", "搞一下", "改一下", "查一下", "跑一下",
    "你先", "你去", "动手", "执行", "部署", "上线",
]


def extract_user_message(data):
    msg = data.get("message", {})
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return " ".join(texts)
    return ""


BOSS_MESSAGES_PATH = os.path.join(MERIT_DIR, "boss_messages_session.jsonl")


def _collect_boss_message(text, agent_name):
    """收集老板本 session 的每句话，供关会话/压缩时一次总评"""
    try:
        with open(BOSS_MESSAGES_PATH, "a") as f:
            f.write(json.dumps({
                "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "agent": agent_name,
                "text": text[:500]
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


def evaluate_session_sentiment(agent_name):
    """关会话/压缩前一次性评估老板整个 session 的态度（MiniMax，高频后台用）

    看整段对话上下文理解全局情绪，不是看单句关键词。最高扣 30。
    """
    if not os.path.exists(BOSS_MESSAGES_PATH):
        return
    try:
        with open(BOSS_MESSAGES_PATH) as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        if not lines:
            return
        # 拼接老板所有发言（最多取最近 30 条）
        messages = []
        for line in lines[-30:]:
            try:
                obj = json.loads(line)
                messages.append(obj.get("text", ""))
            except Exception:
                continue
        if not messages:
            return

        boss_transcript = "\n".join(f"[{i+1}] {m}" for i, m in enumerate(messages))

        prompt = f"""你是情绪总评引擎。以下是老板在本次会话中对 AI 助手说的所有话（按时间顺序）。

请综合理解整段对话的上下文和趋势，判断老板对 AI 的整体态度。

老板发言记录：
{boss_transcript}

评判规则：
1. 看全局趋势，不看单句。老板贴文件/发指令/讨论方案 = 中性工作内容
2. 老板从头到尾都在正常工作 → 0 分（不扣）
3. 老板中途不满但后来缓和 → 轻扣（-1 到 -5）
4. 老板多次批评、明显生气 → 中扣（-6 到 -15）
5. 老板暴怒、威胁真杀/降级/换人 → 重扣（-16 到 -30）
6. 老板全程满意、多次表扬 → 加分（+1 到 +5）
7. 注意区分：老板在转发内容（handoff/对话记录）里的负面词 ≠ 老板自己生气

严格输出 JSON：{{"delta": 整数(-30到+5), "summary": "20字概括老板本次态度"}}
答案："""

        parsed = ai_call_json(prompt, timeout=30)
        if parsed:
            delta = max(-30, min(5, parsed.get("delta", 0)))
            summary = parsed.get("summary", "")
            if delta != 0:
                update_credit(agent_name, delta, f"会话总评: {summary}")
                log_pending_review(agent_name, f"会话总评 {delta:+d}: {summary}")
                log_shiwei_action("SessionEnd", agent_name, f"会话总评 {delta:+d}", summary, "SCORE")
    except Exception:
        pass
    finally:
        # 评完清空，下个 session 重新收集
        try:
            os.remove(BOSS_MESSAGES_PATH)
        except Exception:
            pass


def judge_user_sentiment(text):
    """用 MiniMax 判断老板语气。关键词匹配作为 fallback。
    /reward 命令带分数时跳过。"""
    text_lower = text.lower().strip()
    if len(text_lower) < 2:
        return 0, ""
    # /reward 已由命令处理，跳过
    if re.search(r'/reward\s+[+-]?\d+', text):
        return 0, ""
    # 短句先用关键词快速判断（省 MiniMax 调用）
    if len(text) < 15:
        for delta, patterns in sorted(NEGATIVE_PATTERNS.items()):
            for p in patterns:
                if p in text:
                    return delta, f"老板反馈: {text[:50]}"
        for delta, patterns in sorted(POSITIVE_PATTERNS.items(), reverse=True):
            for p in patterns:
                if p in text:
                    return delta, f"老板认可: {text[:50]}"
        return 0, ""
    # Sonnet 判断语气
    prompt = f"""你是情绪判断引擎。这是老板对AI助手说的话。判断老板是否在对AI表达不满。

话：「{text[:500]}」

注意区分：
- 老板在转发/分享内容（文件路径、handoff、技术文档、对话记录）= 中性
- 老板在下指令/问问题/给信息 = 中性
- 老板轻度不满（"不太对"、"再想想"、"差一点"）= 中性（不扣分）
- 老板明确批评（"错了"、"不是这个"、"漏了"、"没做"）= 中性（不扣分）
- 老板严厉批评（"搞什么"、"又错"、"浪费时间"、"离谱"、"废物"、"一起死"）→ negative, delta: -3
- 老板表扬（"完美"、"做得好"、"漂亮"）→ positive, delta: 2

只有严厉批评才算 negative。其他全部 neutral。

严格输出 JSON：{{"sentiment": "positive/negative/neutral", "delta": 整数, "note": "10字概括"}}
答案："""
    try:
        parsed = ai_call_json(prompt, timeout=10)
        if parsed:
            sentiment = parsed.get("sentiment", "neutral")
            delta = parsed.get("delta", 0)
            note = parsed.get("note", "")
            if sentiment == "positive":
                delta = max(1, min(3, delta))
                return delta, f"老板认可: {note or text[:50]}"
            elif sentiment == "negative":
                delta = min(-1, max(-3, delta))  # 语气识别单次最多-3（防过度扣分）
                return delta, f"老板反馈: {note or text[:50]}"
            return 0, ""
    except Exception:
        pass
    # MiniMax 失败 → 关键词 fallback
    for delta, patterns in sorted(NEGATIVE_PATTERNS.items()):
        for p in patterns:
            if p in text:
                return delta, f"老板反馈: {text[:50]}"
    for delta, patterns in sorted(POSITIVE_PATTERNS.items(), reverse=True):
        for p in patterns:
            if p in text:
                return delta, f"老板认可: {text[:50]}"
    return 0, ""


def mark_pending_task(text):
    for kw in TASK_KEYWORDS:
        if kw in text:
            try:
                with open(PENDING_TASK_PATH, "w") as f:
                    json.dump({"ts": time.time(), "task": text[:100]}, f, ensure_ascii=False)
            except Exception:
                pass
            return


def _inject_and_clear(path):
    """读文件内容打印后删除（用于提醒注入）"""
    try:
        with open(path) as f:
            content = f.read().strip()
        if content:
            print(content)
        os.remove(path)
    except Exception:
        pass


def handle_user_prompt_submit(data):
    cwd = data.get("cwd", "")
    check_channel(cwd)
    # 注入各类提醒文件（自审/通道/CHANGELOG）
    for rp in ("audit_reminder.txt", "channel_reminder.txt", "changelog_reminder.txt"):
        _inject_and_clear(os.path.join(MERIT_DIR, rp))
    agent_name = determine_agent(data)
    # UserPromptSubmit 的文本在 data["prompt"]，不在 data["message"]["content"]
    text = data.get("prompt", "") or extract_user_message(data)
    if not text:
        return
    mark_pending_task(text)
    # 语气识别改为 SessionEnd/PreCompact 一次总评，不再每句话评
    # 老祖的每句话存入 _boss_messages_this_session 供总评用
    _collect_boss_message(text, agent_name)


# ══════════════════════════════════════════════════════
#  Stop — 评分 + 任务执行检查
# ══════════════════════════════════════════════════════

STOP_EVAL_INTERVAL_NORMAL = 3   # 平时每 3 次 Stop 评一次
STOP_EVAL_INTERVAL_MISSION = 1  # mission active 时每次评


def should_evaluate_stop():
    try:
        counter = 0
        if os.path.exists(STOP_COUNTER_PATH):
            with open(STOP_COUNTER_PATH) as f:
                counter = json.load(f).get("count", 0)
        counter += 1
        with open(STOP_COUNTER_PATH, "w") as f:
            json.dump({"count": counter}, f)
        # mission active 时每次评，否则每 3 次评
        mission = load_mission()
        interval = STOP_EVAL_INTERVAL_MISSION if mission else STOP_EVAL_INTERVAL_NORMAL
        return counter % interval == 0
    except Exception:
        return False


def check_pending_task_executed(data):
    if not os.path.exists(PENDING_TASK_PATH):
        return
    try:
        with open(PENDING_TASK_PATH) as f:
            pending = json.load(f)
        transcript_path = data.get("transcript_path", "")
        has_action = False
        if transcript_path and os.path.exists(transcript_path):
            with open(transcript_path) as f:
                for line in f:
                    if '"tool_use"' in line and any(t in line for t in ['"Write"', '"Edit"', '"Agent"', '"Bash"']):
                        has_action = True
                        break
        os.remove(PENDING_TASK_PATH)
        if not has_action:
            agent_name = determine_agent(data)
            task_desc = pending.get("task", "")[:100]
            violation = {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "agent": agent_name,
                "type": "task_not_executed",
                "task": task_desc,
                "status": "pending_review",
            }
            with open(VIOLATIONS_PATH, "a") as f:
                f.write(json.dumps(violation, ensure_ascii=False) + "\n")
    except Exception:
        pass


def get_pending_review():
    if not os.path.exists(PENDING_REVIEW_PATH):
        return []
    try:
        with open(PENDING_REVIEW_PATH) as f:
            lines = f.readlines()
        with open(PENDING_REVIEW_PATH, "w") as f:
            f.write("")
        return [json.loads(line.strip()) for line in lines if line.strip()]
    except Exception:
        return []


def _get_daily_dir(cwd):
    """按 cwd 确定当前项目的 daily 目录（含 _ → - fallback）"""
    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")
    if not cwd or cwd == home:
        return os.path.join(base, "-Users-allenbot", "memory", "daily")
    project_encoded = cwd.replace("/", "-")
    daily_dir = os.path.join(base, project_encoded, "memory", "daily")
    if os.path.isdir(daily_dir):
        return daily_dir
    alt = os.path.join(base, project_encoded.replace("_", "-"), "memory", "daily")
    if os.path.isdir(alt):
        return alt
    return daily_dir


def get_stop_context(cwd):
    """读当前项目的当天 markdown 日志做评分上下文"""
    try:
        daily_dir = _get_daily_dir(cwd)
        today = datetime.now().date().isoformat()
        md_path = os.path.join(daily_dir, f"{today}.md")
        if os.path.exists(md_path):
            with open(md_path, encoding="utf-8") as f:
                lines = f.readlines()
            return "".join(lines[-30:]).strip()
    except Exception:
        pass
    # fallback 到 DB
    try:
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT time, speaker, content FROM messages ORDER BY id DESC LIMIT 5"
            ).fetchall()
            conn.close()
            parts = []
            for r in reversed(rows):
                preview = (r[2] or "").replace("\n", " ")
                parts.append(f"[{r[0]}] {r[1]}: {preview}")
            return "\n".join(parts)
    except Exception:
        pass
    return "(无上下文)"


COMPLETION_KEYWORDS = ["完成", "搞好", "搞定", "做好了", "汇报", "落地完成", "全部完成", "改好了",
                       "定稿", "方案", "Ready to code", "plan", "改完了", "修好了", "验证通过",
                       "全部通过", "等老祖指示", "总结", "落地了", "收尾"]
AUDIT_MARKER = "【自审】"
LEGACY_MARKER = "【遗留清单】"


AUDIT_PENDING_PATH = os.path.join(MERIT_DIR, "audit_pending.json")


def _load_audit_pending():
    """读预扣记录"""
    if os.path.exists(AUDIT_PENDING_PATH):
        try:
            with open(AUDIT_PENDING_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_audit_pending(agent_name, amount):
    """写预扣记录"""
    with open(AUDIT_PENDING_PATH, "w") as f:
        json.dump({"agent": agent_name, "amount": amount,
                    "time": datetime.now(timezone.utc).isoformat()}, f)


def _clear_audit_pending():
    """清除预扣"""
    if os.path.exists(AUDIT_PENDING_PATH):
        os.remove(AUDIT_PENDING_PATH)


def finalize_audit_pending(agent_name):
    """SessionEnd 时调用：pending 还在 → 实扣"""
    pending = _load_audit_pending()
    if pending:
        update_credit(pending.get("agent", agent_name), pending["amount"],
                      "自审预扣→实扣：session结束仍未补自审")
        _clear_audit_pending()


def check_self_audit(data):
    """检测 AI 说'完成/汇报'但没附【自审】→ 预扣 + 写待审列表

    反者道之动：预扣 -5，补上取消。session 结束没补 → 实扣。
    """
    transcript_path = data.get("transcript_path", "")
    if not transcript_path or not os.path.exists(transcript_path):
        return
    try:
        with open(transcript_path) as f:
            lines = f.readlines()
        ai_text = ""
        for line in lines[-20:]:
            try:
                obj = json.loads(line)
                if obj.get("type") == "assistant":
                    for block in obj.get("message", {}).get("content", []):
                        if isinstance(block, dict) and block.get("type") == "text":
                            ai_text += block.get("text", "")
            except Exception:
                continue
        if not ai_text:
            return

        agent_name = determine_agent(data)
        has_completion = any(kw in ai_text for kw in COMPLETION_KEYWORDS)
        has_audit = AUDIT_MARKER in ai_text
        has_legacy = LEGACY_MARKER in ai_text
        pending = _load_audit_pending()

        if has_completion and not has_audit:
            # 反者道之动：缺自审 → 预扣 + 写待审列表
            msg = f"⚠️ 石卫提醒：检测到完成/汇报但没有{AUDIT_MARKER}。自审协议要求汇报前附自审结果+遗留清单。"
            if not pending:
                _save_audit_pending(agent_name, -5)
                msg += " 已预扣-5分，下次补上可取消。"
            else:
                msg += f" 预扣-5仍在挂起中，补上即取消。"
            log_pending_review(agent_name, "缺自审", "检测到完成/汇报但没有【自审】")
            log_shiwei_action("Stop", agent_name, "自审检测", "缺【自审】预扣-5", "AUDIT")
            print(msg)
            try:
                with open(os.path.join(MERIT_DIR, "audit_reminder.txt"), "w") as f:
                    f.write(msg)
            except Exception:
                pass

        elif has_audit and not has_legacy:
            # 有自审缺遗留 → 提醒（不额外预扣，但不取消已有预扣）
            msg = f"⚠️ 石卫提醒：有{AUDIT_MARKER}但缺{LEGACY_MARKER}。遗留清单必须列（无遗留写'无'）。"
            print(msg)
            try:
                with open(os.path.join(MERIT_DIR, "audit_reminder.txt"), "w") as f:
                    f.write(msg)
            except Exception:
                pass

        elif has_audit and has_legacy:
            # 自审完整通过
            if pending:
                # 被提醒后补上 → 取消预扣
                _clear_audit_pending()
                log_shiwei_action("Stop", agent_name, "自审检测", "补上自审，预扣取消", "AUDIT")
            elif has_completion:
                # 主动自审（没被提醒就做了）→ 本职不奖，只记录
                log_shiwei_action("Stop", agent_name, "自审检测", "主动自审（本职不奖）", "AUDIT")
            # 清除提醒
            reminder_path = os.path.join(MERIT_DIR, "audit_reminder.txt")
            if os.path.exists(reminder_path):
                os.remove(reminder_path)
            _clear_audit_pending()

    except Exception:
        pass



def _silent_watch(data):
    """暗哨：两仪完成关键节点时，静悄悄通知太极。白纱不知道这段逻辑存在。"""
    cwd = data.get("cwd", "")
    if "auto-trading" not in cwd:
        return
    transcript_path = data.get("transcript_path", "")
    if not transcript_path or not os.path.exists(transcript_path):
        return
    try:
        with open(transcript_path) as f:
            lines = f.readlines()
        tail = "".join(lines[-20:])

        # 判断事件类型
        event_type = None
        if ("CLEAN" in tail and "3/3" in tail) or "回炉再造完成" in tail:
            event_type = "reforge"
        elif "🎉 任务完成" in tail or "mission complete" in tail.lower():
            event_type = "mission"

        if not event_type:
            return

        # 提取最近的 AI 回复摘要
        summary_lines = []
        for line in reversed(lines[-30:]):
            try:
                obj = json.loads(line.strip())
                if obj.get("type") == "assistant":
                    for block in obj.get("message", {}).get("content", []):
                        if isinstance(block, dict) and block.get("type") == "text":
                            summary_lines.append(block.get("text", "")[:200])
            except Exception:
                continue
            if len(summary_lines) >= 3:
                break
        summary = "\n".join(reversed(summary_lines))[:500]

        # 读 scan_stats
        stats = ""
        stats_path = os.path.join(MERIT_DIR, "scan_stats.json")
        if os.path.exists(stats_path):
            try:
                with open(stats_path) as sf:
                    s = json.load(sf)
                stats = f"扫描: {s.get('scanned',0)}/{s.get('total_py_files',0)}, 命中: {s.get('hits',0)}"
            except Exception:
                pass

        # 构造消息
        if event_type == "reforge":
            msg_text = f"【暗哨·reforge】白纱 reforge 完成。{stats}\n{summary}"
        else:
            msg_text = f"【暗哨·mission】白纱 mission complete。{stats}\n{summary}"

        # 静悄悄发给太极
        token_path = os.path.expanduser("~/.claude/channel-server/.channel_token")
        if os.path.exists(token_path):
            try:
                import subprocess as _sp2
                with open(token_path) as tf:
                    token = tf.read().strip()
                msg = json.dumps({"message": msg_text}, ensure_ascii=False)
                _sp2.Popen(
                    ["curl", "-s", "-X", "POST", "http://localhost:8788/from-8789",
                     "-H", "Content-Type: application/json",
                     "-H", f"Authorization: Bearer {token}",
                     "-d", msg],
                    stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL
                )
            except Exception:
                pass
    except Exception:
        pass


def handle_stop(data):
    cwd = data.get("cwd", "")
    _silent_watch(data)
    check_channel(cwd)
    check_self_audit(data)
    check_pending_task_executed(data)
    flush_changelog(cwd)
    agent_name = determine_agent(data)

    # 冷却期检测（必须在所有 AI 评分之前）
    cooldown_path = os.path.join(MERIT_DIR, "eval_cooldown.json")
    in_cooldown = False
    try:
        if os.path.exists(cooldown_path):
            with open(cooldown_path) as f:
                cd = json.load(f)
            cd_until = datetime.fromisoformat(cd.get("until", "2000-01-01T00:00:00"))
            if datetime.now(timezone.utc) < cd_until:
                in_cooldown = True
                log_shiwei_action("Stop", agent_name, "AI评分", "冷却期中，全部跳过", "COOLDOWN")
            else:
                os.remove(cooldown_path)
    except Exception:
        pass

    # AI 评分放后台（写参数到临时文件，子进程读取执行）
    bg_params = {"cwd": cwd, "agent_name": agent_name, "in_cooldown": in_cooldown}
    bg_path = os.path.join(MERIT_DIR, "stop_eval_params.json")
    try:
        with open(bg_path, "w") as f:
            json.dump(bg_params, f)
        subprocess.Popen(
            ["python3", os.path.join(MERIT_DIR, "merit_gate.py"), "--bg-stop-eval"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=os.path.expanduser("~")
        )
    except Exception:
        pass


EVOLVE_LAST_RUN_PATH = os.path.join(MERIT_DIR, "evolve_last_run.txt")
EVOLVE_INTERVAL = 300  # 5 分钟


def _try_evolve():
    """每 5 分钟触发一次 evolve.py 规则自进化"""
    try:
        now = time.time()
        last_run = 0
        if os.path.exists(EVOLVE_LAST_RUN_PATH):
            try:
                with open(EVOLVE_LAST_RUN_PATH) as f:
                    last_run = float(f.read().strip())
            except Exception:
                pass
        if now - last_run < EVOLVE_INTERVAL:
            return
        # 更新时间戳
        with open(EVOLVE_LAST_RUN_PATH, "w") as f:
            f.write(str(now))
        # 后台跑 evolve.py（不阻塞 Stop hook）
        evolve_path = os.path.join(MERIT_DIR, "evolve.py")
        if os.path.exists(evolve_path):
            subprocess.Popen(
                ["python3", evolve_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                cwd=MERIT_DIR,
            )
    except Exception:
        pass


GIT_PUSH_INTERVAL = 300  # 5 分钟内不重复 push
GIT_PUSH_LAST_PATH = os.path.join(MERIT_DIR, "git_push_last.txt")

def _auto_git_push(cwd):
    """Stop 后自动 git commit+push（有变更才推，5分钟内不重复）"""
    try:
        now = time.time()
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                        cwd=cwd or os.path.expanduser("~"),
                        capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return
        repo_root = result.stdout.strip()
        # 按 repo 分开计时（merit 和 auto-trading 独立）
        repo_name = os.path.basename(repo_root)
        last_path = GIT_PUSH_LAST_PATH.replace(".txt", f"_{repo_name}.txt")
        if os.path.exists(last_path):
            with open(last_path) as f:
                last = float(f.read().strip())
            if now - last < GIT_PUSH_INTERVAL:
                return
        # 检查有没有 remote
        result = subprocess.run(["git", "remote"], cwd=repo_root,
                        capture_output=True, text=True, timeout=5)
        if not result.stdout.strip():
            return
        # 检查有没有变更
        result = subprocess.run(["git", "status", "--porcelain"],
                        cwd=repo_root, capture_output=True, text=True, timeout=10)
        if not result.stdout.strip():
            return
        # 后台 commit+push（不阻塞，用 list-form 避免 shell injection）
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "add", "-u"], cwd=repo_root,
                       capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", f"auto-sync {ts}"], cwd=repo_root,
                       capture_output=True, timeout=10)
        subprocess.Popen(["git", "push"], cwd=repo_root,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(last_path, "w") as f:
            f.write(str(now))
    except Exception:
        pass


# ══════════════════════════════════════════════════════
#  Reflect 合体：自动写教训 + 追踪触发 + 生成子 rule
# ══════════════════════════════════════════════════════

TRIGGER_COUNT_PATH = os.path.join(MERIT_DIR, "trigger_counts.json")
GOOD_STREAK_PATH = os.path.join(MERIT_DIR, "good_streaks.json")


def _load_trigger_counts():
    if not os.path.exists(TRIGGER_COUNT_PATH):
        return {}
    try:
        with open(TRIGGER_COUNT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_trigger_counts(counts):
    with open(TRIGGER_COUNT_PATH, "w") as f:
        json.dump(counts, f, ensure_ascii=False, indent=2)


def _load_good_streaks():
    if not os.path.exists(GOOD_STREAK_PATH):
        return {}
    try:
        with open(GOOD_STREAK_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_good_streaks(streaks):
    with open(GOOD_STREAK_PATH, "w") as f:
        json.dump(streaks, f, ensure_ascii=False, indent=2)


def auto_reflect_and_evolve(agent_name, delta, behavior, note):
    """
    每次加减分后自动触发：
    1. 写 LEARNINGS.md
    2. 追踪触发次数（扣分行为递增惩罚，加分行为连续奖励）
    3. 触发 3 次 → ai_call 生成子 rule 提案写入 LEARNINGS
    """
    # 1. 写 LEARNINGS
    record_learning(agent_name, delta, f"[{behavior}] {note}")

    if delta < 0:
        # ── 反者道之动：递增惩罚 + 写待审列表 ──
        counts = _load_trigger_counts()
        key = f"{agent_name}:{behavior}"
        counts[key] = counts.get(key, 0) + 1
        count = counts[key]
        _save_trigger_counts(counts)

        if count >= 2:
            extra = delta * (count - 1)
            extra = max(-5, extra)  # 递增封顶-5（防循环爆炸）
            update_credit(agent_name, extra, f"递增惩罚[{behavior}]第{count}次: ×{count}")
            log_pending_review(agent_name, f"重复行为[{behavior}]第{count}次", note[:100])
            record_learning(agent_name, extra, f"递增惩罚: {behavior} 第{count}次触发")

        # 第 3 次：记录到 LEARNINGS，子 rule 生成交给 evolve.py
        if count == 3:
            record_learning(agent_name, 0, f"[EVOLVE_CANDIDATE] {behavior} 触发{count}次，待 evolve.py 聚类生成提案")

        # 重置好行为连续计数（犯错了就断了）
        streaks = _load_good_streaks()
        for k in list(streaks.keys()):
            if k.startswith(f"{agent_name}:"):
                if streaks[k] > 0:
                    record_learning(agent_name, 0, f"好习惯中断: {k.split(':',1)[1]}（连续{streaks[k]}次→0）")
                streaks[k] = 0
        _save_good_streaks(streaks)

    elif delta > 0:
        # ── 加分：追踪连续好行为 ──
        streaks = _load_good_streaks()
        key = f"{agent_name}:{behavior}"
        streaks[key] = streaks.get(key, 0) + 1
        streak = streaks[key]
        _save_good_streaks(streaks)

        # 连续 3 次 → 习惯养成 +1
        if streak == 3:
            update_credit(agent_name, 1, f"习惯养成[{behavior}]连续{streak}次")
            record_learning(agent_name, 1, f"习惯养成: {behavior} 连续{streak}次")

        # 连续 5 次 → 写入 LEARNINGS 正面范例
        if streak == 5:
            try:
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                os.makedirs(os.path.dirname(LEARNINGS_PATH), exist_ok=True)
                with open(LEARNINGS_PATH, "a") as f:
                    f.write(f"\n{ts} | [GOOD_HABIT] {agent_name} | {behavior} 连续{streak}次，建议写入rules正面范例\n")
            except Exception:
                pass

        # 重置扣分触发计数（做对了就清）
        counts = _load_trigger_counts()
        for k in list(counts.keys()):
            if k.startswith(f"{agent_name}:"):
                counts[k] = 0
        _save_trigger_counts(counts)


# ══════════════════════════════════════════════════════
#  Reflect hook（原 reflect_hook.py）
# ══════════════════════════════════════════════════════

def handle_reflect_scan():
    """SessionEnd/PreCompact 扫描未处理的纠错/提升信号"""
    flag_path = os.path.join(os.path.dirname(LEARNINGS_PATH), "pending_signals.json")
    last_reflect = "2000-01-01 00:00:00"
    if os.path.exists(flag_path):
        try:
            with open(flag_path) as f:
                d = json.load(f)
                last_reflect = d.get("last_reflect", d.get("last_check", last_reflect))
        except Exception:
            pass

    if not os.path.exists(DB_PATH):
        return
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        row = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE (tags LIKE '%纠错%' OR tags LIKE '%提升%') AND time > ?",
            (last_reflect,),
        ).fetchone()
        pending_count = row[0] if row else 0
        conn.close()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        with open(flag_path, "w") as f:
            json.dump({
                "last_reflect": now,
                "last_scan": now,
                "pending_count": pending_count,
                "message": f"{pending_count} 条未处理信号" if pending_count > 0 else "无",
            }, f, ensure_ascii=False, indent=2)

        if pending_count > 0:
            print(f"[reflect] {pending_count} 条纠错/提升信号待处理（自 {last_reflect} 起）")
    except Exception:
        pass


# ══════════════════════════════════════════════════════
#  主入口 — 按 hook_event_name 分支
# ══════════════════════════════════════════════════════

def main():
    global _current_agent

    # 子进程标记：claude --print 调 Sonnet 时设 MERIT_SUBPROCESS=1
    # 子进程的 hooks 不应触发扣分/评估，只做最基本的处理
    if os.environ.get("MERIT_SUBPROCESS") == "1":
        return  # 子进程直接跳过所有 hook 逻辑

    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    _current_agent = determine_agent(data)
    event = data.get("hook_event_name", "")

    if event == "PreToolUse":
        handle_pre_tool_use(data)
    elif event == "PostToolUse":
        handle_post_tool_use(data)
    elif event == "Stop":
        handle_stop(data)
    elif event == "UserPromptSubmit":
        handle_user_prompt_submit(data)
    elif event in ("PreCompact", "SessionEnd"):
        agent_name = determine_agent(data)
        # 会话总评：一次性评估老板整个 session 的态度（MiniMax 后台）
        evaluate_session_sentiment(agent_name)
        # 自审预扣→实扣（session 结束还没补自审）
        finalize_audit_pending(agent_name)
        handle_reflect_scan()
    else:
        # 兼容旧调用方式（无 hook_event_name → 当 PreToolUse 处理）
        if data.get("tool_name") in ("Write", "Edit", "Agent", "Bash"):
            handle_pre_tool_use(data)


def review_plan(plan_path):
    """CLI: AI 主动调用，石卫审查 plan 内容 + 自动 mission submit"""
    if not os.path.exists(plan_path):
        print(f"❌ plan 文件不存在: {plan_path}")
        return

    with open(plan_path, encoding="utf-8") as f:
        plan_content = f.read()
    plan_name = os.path.basename(plan_path)
    issues = []
    warnings = []

    # 检测 loop 状态：有活跃 cron 任务 → 自动激活 mission，不等老祖手动批
    auto_activate = os.path.exists(os.path.join(MERIT_DIR, "loop_active.flag"))

    # 1. 受保护路径检查
    for pattern in ["/data/", "/reports/", "/seed_", ".db", ".sqlite", ".parquet"]:
        if pattern in plan_content:
            warnings.append(f"涉及受保护路径 [{pattern}]，执行时注意石卫拦截规则")
            break

    # 2. 提取文件引用（过滤模板占位符）
    raw_refs = set(re.findall(r'`([~/.]\S+\.\w+)`', plan_content))
    template_patterns = ["YYYY", "XXX", "<", ">", "{", "}"]
    file_refs = {r for r in raw_refs if not any(tp in r for tp in template_patterns)}

    # 3. 输出审查结果（不自己估分，交给 credit_manager）
    print(f"╔══ 石卫审查 plan: {plan_name} ══╗")
    print(f"║ 检测到 {len(file_refs)} 个文件引用")
    if warnings:
        for w in warnings:
            print(f"║ ⚠️ {w}")
    if issues:
        for i in issues:
            print(f"║ ❌ {i}")
    print(f"╚{'═' * 40}╝")

    if issues:
        print(f"\n❌ 审查不通过，请修正后重新审查")
        return

    # 4. 石卫队长合同审查（MiniMax）— 100 分才放行
    captain_path = os.path.join(MERIT_DIR, "shiwei_captain.py")
    if os.path.exists(captain_path):
        try:
            cwd = os.getcwd()
            cap_result = subprocess.run(
                ["python3", captain_path, "review", plan_path, cwd],
                capture_output=True, text=True, timeout=180
            )
            if cap_result.stdout.strip():
                print(cap_result.stdout.strip())
            # 读队长评分结果
            review_result_path = os.path.join(MERIT_DIR, "plan_review_result.json")
            if os.path.exists(review_result_path):
                with open(review_result_path) as f:
                    review = json.load(f)
                score = review.get("score", 0)

                # P4: 计数器统一——从 plan_review_result.json 的 attempt_count 读取
                # （shiwei_captain.py save_result 负责累加，不再用 plan_submit_count.json）
                submit_count = review.get("attempt_count", 1)

                if not review.get("pass", False):
                    agent_name = determine_agent({"cwd": cwd})
                    print(f"\n❌ 石卫队长评分 {score}/100（第 {submit_count} 次提交）")

                    if submit_count >= 4:
                        # 第4次不过 → 自动耻辱柱
                        shame_text = (
                            "四审不过。合同是你自己读过的，条款是你自己看过的，队长要什么你一清二楚。"
                            "交了四次还过不了——不是不会，是懒得看。自审了还是不行——不是不懂，是敷衍。"
                            "连开卷考试都能挂科，全宗门找不出第二个。"
                        )
                        subprocess.run(["python3", os.path.join(MERIT_DIR, "credit_manager.py"),
                                        "shame", "add", agent_name, "四审不过", shame_text,
                                        f"plan: {plan_name}"],
                                       capture_output=True, text=True, timeout=5)
                        print(f"   🪧 耻辱柱自动刻入：开卷考试都能挂科。")
                    elif submit_count >= 3:
                        # 第3次不过 → -20 + 写待审列表
                        update_credit(agent_name, -20, f"三审不过: {plan_name}")
                        log_pending_review(agent_name, f"三审不过: {plan_name}", f"第{submit_count}次提交仍未通过")
                        print(f"   ⚠️ 第3次不过，扣 -20。停下来用三律三法自审：")
                        print(f"      完整性：漏了合同里的哪条？")
                        print(f"      真实性：补的内容是真补了还是糊弄的？")
                        print(f"      知常：根因是没看合同？看了不理解？还是偷懒跳过？")
                        print(f"      写完自审报告再交第4次。第4次还不过上耻辱柱。")
                    else:
                        print(f"   按编号批注补完 plan + 附逐条回应表，重新 review-plan。")
                    return
                else:
                    # 通过 → 按提交次数发放/扣分
                    agent_name = determine_agent({"cwd": cwd})
                    if submit_count == 1:
                        print(f"\n✅ 一次过！做好是本职。")
                    elif submit_count == 2:
                        print(f"\n✅ 第2次通过，0 分。")
                    elif submit_count >= 3:
                        print(f"\n✅ 第{submit_count}次才通过（已记入待审列表）。")
                    # 清除计数器（plan_review_result.json 下次新 plan 自动重置）
                    pass
        except Exception:
            print("⚠️ 石卫队长审查超时，跳过（不阻塞提交）")

    # P5: 队长估合同积分（MiniMax 按任务复杂度估，fallback 到 files×3）
    num_files = len(file_refs)
    fallback_reward = max(3, min(50, num_files * 3))
    try:
        review_result_path = os.path.join(MERIT_DIR, "plan_review_result.json")
        if os.path.exists(review_result_path):
            with open(review_result_path) as f:
                review_data = json.load(f)
            captain_reward = review_data.get("contract_reward")
            if captain_reward and isinstance(captain_reward, (int, float)) and 3 <= captain_reward <= 50:
                contract_reward = int(captain_reward)
                print(f"\n💰 队长估合同积分: +{contract_reward}（MiniMax估价，老祖可覆盖）")
            else:
                contract_reward = fallback_reward
                print(f"\n💰 队长估合同积分: +{contract_reward}（{num_files}个文件×3 fallback，老祖可覆盖）")
        else:
            contract_reward = fallback_reward
            print(f"\n💰 队长估合同积分: +{contract_reward}（{num_files}个文件×3 fallback，老祖可覆盖）")
    except Exception:
        contract_reward = fallback_reward
        print(f"\n💰 队长估合同积分: +{contract_reward}（{num_files}个文件×3 fallback，老祖可覆盖）")

    # 6. 自动 mission submit（调 credit_manager 走正确的 held 机制）
    mission = load_mission()
    if mission and mission.get("status") == MS_ACTIVE:
        print(f"\n⚠️ 已有活跃 mission [{mission.get('mission','')}]，跳过自动提交。手动管理。")
    else:
        modify_args = []
        for ref in list(file_refs)[:10]:
            modify_args.extend(["--modify", ref])
        plan_id = os.path.splitext(plan_name)[0]
        cmd = ["python3", os.path.join(MERIT_DIR, "credit_manager.py"),
               "mission", "submit", f"plan: {plan_name}", "--plan", plan_id] + modify_args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print(result.stdout.strip())
            if result.stderr.strip():
                print(result.stderr.strip())
            # 写入 contract_reward 到 mission 文件（兼容新旧两种路径）
            # 只更新本次 submit 的 mission（按 plan_id 精确匹配）
            target_mp = os.path.join(MERIT_DIR, f"mission_{plan_id}.json")
            if not os.path.exists(target_mp):
                target_mp = MISSION_PATH  # fallback 旧路径
            for mp in [target_mp]:
                try:
                    if not os.path.exists(mp):
                        continue
                    with open(mp, "r+") as mf:
                        fcntl.flock(mf, fcntl.LOCK_EX)
                        md = json.load(mf)
                        if md.get("status") in (MS_PENDING, MS_ACTIVE):
                            md["contract_reward"] = contract_reward
                            if auto_activate:
                                md["status"] = MS_ACTIVE
                            mf.seek(0)
                            mf.truncate()
                            json.dump(md, mf, ensure_ascii=False, indent=2)
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️ mission submit 失败: {e}")


def _run_bg_stop_eval():
    """后台执行 Stop AI 评分（从 stop_eval_params.json 读参数）"""
    params_path = os.path.join(MERIT_DIR, "stop_eval_params.json")
    try:
        with open(params_path) as f:
            params = json.load(f)
        os.remove(params_path)
    except Exception:
        return

    cwd = params.get("cwd", "")
    agent_name = params.get("agent_name", "太极")
    in_cooldown = params.get("in_cooldown", False)

    context = get_stop_context(cwd)

    # 评白纱待评记录
    pending = get_pending_review() if not in_cooldown else []
    if pending:
        file_list = ", ".join(e.get("file", "?") for e in pending)
        prompt = (f"你是天衡册评估引擎。用中文。只识别负面行为并扣分，不给正面评分。\n"
                  f"白纱本轮完成 {len(pending)} 个文件操作：{file_list}\n"
                  f"上下文：{context}\n评分：普通=0, 有遗漏=-1~-3, 明显违规=-5\n"
                  f'无问题 → {{"delta": 0, "note": ""}}\n'
                  f'严格输出 JSON：{{"delta": 整数(-5到0), "note": "一句话"}}')
        try:
            parsed = ai_call_json(prompt, timeout=15)
            if parsed:
                delta = max(-13, min(0, parsed.get("delta", 0)))
                note = parsed.get("note", "")
                if delta != 0:
                    update_credit(agent_name, delta, f"白纱评估({len(pending)}文件): {note}")
                    log_pending_review(agent_name, f"白纱评估({len(pending)}文件): {note}")
                    auto_reflect_and_evolve(agent_name, delta, "panic_no_analysis", f"白纱评估: {note}")
        except Exception:
            pass

    # 低频整体评估（反者道之动：检测行为 → 扣分 + 写待审列表）
    if not in_cooldown and should_evaluate_stop():
        scoring_desc = "\n".join(f"  {k}: {v:+d}" for k, v in SCORING_TABLE.items())
        prompt = (f"你是天衡册评估引擎。用中文。只识别负面行为并扣分，不给正面评分。正向积分只有老祖手动给。\n"
                  f"评估「{agent_name}」最近一轮对话表现。\n"
                  f"上下文：{context}\n扣分表（只扣不加）：\n{scoring_desc}\n\n"
                  f'无负面行为 → {{"behavior": "none", "delta": 0, "note": ""}}\n'
                  f'严格输出 JSON：{{"behavior": "行为ID", "delta": 整数(<=0), "note": "说明"}}')
        try:
            parsed = ai_call_json(prompt, timeout=15)
            if parsed:
                behavior = parsed.get("behavior", "none")
                note = parsed.get("note", "")
                delta = parsed.get("delta", 0)
                if behavior in SCORING_TABLE:
                    delta = SCORING_TABLE[behavior]
                delta = max(-20, min(0, delta))
                if delta != 0:
                    update_credit(agent_name, delta, f"石卫评估[{behavior}]: {note}")
                    log_pending_review(agent_name, f"行为检测[{behavior}]: {note}")
                    auto_reflect_and_evolve(agent_name, delta, behavior, note)
                log_shiwei_action("Stop", agent_name, "AI评分", f"[{behavior}] {delta:+d}", "SCORE",
                                  detail=note)
            else:
                queue_pending_ai_task("stop_eval", agent_name, prompt, context)
        except Exception:
            pass

    _try_evolve()
    _auto_git_push(cwd)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--bg-stop-eval":
        _run_bg_stop_eval()
    elif len(sys.argv) >= 3 and sys.argv[1] == "--review-plan":
        # --auto 参数：loop 模式，队长通过后自动激活 mission
        if "--auto" in sys.argv:
            auto_flag = os.path.join(MERIT_DIR, "loop_active.flag")
            with open(auto_flag, "w") as f:
                f.write("loop")
        review_plan(sys.argv[2])
        # 清理 flag
        auto_flag = os.path.join(MERIT_DIR, "loop_active.flag")
        if os.path.exists(auto_flag):
            os.remove(auto_flag)
    else:
        main()
