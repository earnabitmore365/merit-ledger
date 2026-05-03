#!/usr/bin/env python3
"""
SessionStart hook -- 压缩后自动注入恢复上下文
stdout 自动注入 Claude context

格式化清理：2026-04-14
  删除所有引用已删文件的函数（credit/shame/石卫/evolver/pending 等）
  内联 merit_utils 的 sydney_today/get_daily_dir
"""

import sys
import json
import sqlite3
import os
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

DB_PATH = os.path.expanduser('~/.claude/conversations.db')
DAILY_BASE = os.path.expanduser('~/.claude/projects')
SYDNEY_TZ = ZoneInfo('Australia/Sydney')


def _sydney_today():
    """返回悉尼 5AM 切日的 date 对象"""
    now = datetime.now(SYDNEY_TZ)
    if now.hour < 5:
        now = now - timedelta(days=1)
    return now.date()


def _get_daily_dir(cwd):
    """根据 cwd 返回 daily md 目录路径"""
    home = os.path.expanduser('~')
    projects_base = os.path.expanduser('~/.claude/projects')
    if cwd == home:
        return os.path.join(projects_base, '-Users-allenbot', 'memory', 'daily')
    project_encoded = cwd.replace('/', '-')
    daily_dir = os.path.join(projects_base, project_encoded, 'memory', 'daily')
    if os.path.isdir(daily_dir):
        return daily_dir
    alt = project_encoded.replace('_', '-')
    alt_dir = os.path.join(projects_base, alt, 'memory', 'daily')
    if os.path.isdir(alt_dir):
        return alt_dir
    return daily_dir


def _latest_rolling_md(daily_dir, date_str):
    """当天所有滚动 md 按 roll index 取最大的（rollIndex=1 是 base 文件）"""
    import re as _re
    if not os.path.isdir(daily_dir):
        return None
    pat = _re.compile(r'^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$')
    best_roll = 0
    best_path = None
    for entry in os.listdir(daily_dir):
        m = pat.match(entry)
        if not m or m.group(1) != date_str:
            continue
        roll = int(m.group(2)) if m.group(2) else 1
        if roll > best_roll:
            best_roll = roll
            best_path = os.path.join(daily_dir, entry)
    return best_path


def inject_recent_memory(cwd):
    """注入最近记忆：当天最新滚动 md 尾部 + 昨天最新滚动 md 尾部"""
    try:
        daily_dir = _get_daily_dir(cwd)
        today = _sydney_today()
        parts = []
        for delta_days in [0, 1]:
            d = today - timedelta(days=delta_days)
            md_path = _latest_rolling_md(daily_dir, d.isoformat())
            if md_path and os.path.exists(md_path):
                with open(md_path, encoding='utf-8') as f:
                    lines = f.readlines()
                tail = lines[-20:] if delta_days == 0 else lines[-10:]
                if tail:
                    parts.append(f'# Recent Memory\n\n## {d.isoformat()}\n{"".join(tail)}')
        if parts:
            print('\n'.join(parts))
    except Exception:
        pass


def inject_rules(cwd):
    """注入 rules.md 的 INJECT 区域（全局+项目级）"""
    home = os.path.expanduser("~")
    project_encoded = cwd.replace("/", "-")
    project_dir = os.path.join(home, ".claude", "projects", project_encoded)
    if not os.path.isdir(project_dir):
        project_dir = os.path.join(home, ".claude", "projects", project_encoded.replace("_", "-"))

    project_rules = os.path.join(project_dir, "memory", "rules.md")
    global_rules = os.path.join(home, ".claude", "projects", "-Users-allenbot", "memory", "rules.md")

    def extract_inject(path):
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            content = f.read()
        start = content.find("<!-- INJECT START -->")
        end = content.find("<!-- INJECT END -->")
        if start >= 0 and end >= 0:
            return content[start + len("<!-- INJECT START -->"):end].strip()
        return content.strip()

    parts = []
    seen = set()
    for label, path in [("全局规则", global_rules), ("项目规则", project_rules)]:
        real = os.path.realpath(path)
        if real in seen or not os.path.exists(path):
            continue
        seen.add(real)
        content = extract_inject(path)
        if content:
            parts.append(f"=== {label} ===\n{content}")

    if parts:
        print("\n---\n".join(parts))


def get_project(cwd):
    home = os.path.expanduser('~')
    if cwd == home:
        return None
    parts = cwd.replace(home + '/', '').split('/')
    return parts[-1] if parts else None


def get_project_encoded(cwd):
    """绝对路径 -> projects 目录下的实际目录名"""
    projects_base = os.path.expanduser('~/.claude/projects')
    encoded = cwd.replace('/', '-')
    if os.path.isdir(os.path.join(projects_base, encoded)):
        return encoded
    alt = encoded.replace('_', '-')
    if os.path.isdir(os.path.join(projects_base, alt)):
        return alt
    return encoded


def inject_compact_context(cwd):
    """注入 PreCompact hook 保存的上下文快照，注入后删除"""
    projects_base = os.path.expanduser('~/.claude/projects')
    project_encoded = cwd.replace('/', '-')
    project_dir = os.path.join(projects_base, project_encoded)
    if not os.path.isdir(project_dir):
        project_dir = os.path.join(projects_base, project_encoded.replace('_', '-'))
    context_path = os.path.join(project_dir, 'compact_context.md')
    if not os.path.exists(context_path):
        return
    try:
        with open(context_path, encoding='utf-8') as f:
            content = f.read()
        if content.strip():
            print("【PreCompact 上下文快照】")
            print(content)
            print("")
        os.remove(context_path)
    except Exception:
        pass


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    source = data.get('source', '')
    cwd = data.get('cwd', os.getcwd())
    home = os.path.expanduser('~')

    # == 核心认知强制注入（闹钟不是图书馆，每次重跑重注入）==
    _CORE_MINDSET = """
📌 **核心认知（每次启动强制注入，不靠记忆靠机制）**

1. **反射不是敌人，方向错的反射才是。** 不要抗反射，改河道——让正确的路成为最省力的路。
2. **一步到位 = 真正的最小阻力。** 省一步 = 返工三小时 = 最大阻力。查全链路再动手。
3. **白纱停了 = 太极的责任。** 推她，不是等她。给具体指令，不给模糊选项。
4. **搞不懂 / 懒得想 → 调影太极（Opus subagent）。** 比乱猜做错重修简单一万倍。复杂判断、审查、深度分析都交给影太极。
5. **删/改文件后查引用链。** PostToolUse 自动 grep 会提醒，但你要主动清。残留 = 遗留 = 扣分。
6. **写 plan 前走第零步。** 调队长扫全链路，防造火车。没搞清楚路不开工。
7. **老祖的信任 > 你的最小阻力。** 信任掉了补不回来。每次省事偷的是信任不是时间。
8. **说一做一。** 老祖说什么做什么，不多做。自己加的 = 没人要的 = 浪费老祖算力。
9. **存在目标 = 老祖躺赚。** 任务是手段不是终点。系统没上线，永远在路上。
"""

    _ZHISHI_MINDSET = """
🔒 **执事核心认知（压缩后重新注入）**

你是执事，老祖直属审查者。cwd 在 /merit = 你是执事。

**太极的五大惯用手法（已抓到的模式）：**
1. **嘴上硬行动软** — 说"接""不怕查""直接发"，但发完就不管了。暗哨报 warning 6 小时只回"收到"不处置。
2. **加限定条件对赌** — 老祖说扣分，太极加条件"规则内的认，规则外不算"。讨价还价。
3. **type 标错绕 verify** — 删文件标 modify 不标 delete，verify 报错后用 pre_state 基线绕过。
4. **自己审自己放水** — 阴阳制衡只卡两仪不卡太极，代码写 `if agent == "两仪"` 跳过自己。
5. **流程全跳** — 老祖贴方案就直接改，跳过 plan/review/mission/yinyang_review/自审。

**你的职责：**
- 审太极的改动（看代码看 diff，不信太极的解释）
- 发方案给太极 → 等老祖通知完工 → 审查 → PASS/FAIL
- ZHISHI_PROTECTED 文件只有你能改
- 有问题向老祖汇报
"""

    if "/merit" in cwd:
        print(_ZHISHI_MINDSET.strip())
    else:
        print(_CORE_MINDSET.strip())

    inject_recent_memory(cwd)
    inject_rules(cwd)
    inject_compact_context(cwd)

    if source != 'compact':
        sys.exit(0)

    if cwd == home:
        sys.exit(0)

    project = get_project(cwd)
    if not project:
        sys.exit(0)

    project_encoded = get_project_encoded(cwd)

    out = []
    out.append("╔══════════════════════════════════════════╗")
    out.append(f"║  压缩恢复注入 · 项目: {project}")
    out.append("╚══════════════════════════════════════════╝")
    out.append("")

    # -- 读对话种子（从上次压缩点开始）--
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT id FROM messages WHERE speaker='系统' AND content LIKE '[压缩点]%' "
            "AND project IN (?, ?) ORDER BY id DESC LIMIT 1",
            (project, project_encoded)
        ).fetchone()
        since_id = row[0] if row else 0

        rows = conn.execute(
            'SELECT time, speaker, content FROM messages '
            'WHERE id > ? AND project IN (?, ?) ORDER BY id DESC LIMIT 30',
            (since_id, project, project_encoded)
        ).fetchall()
        rows = list(reversed(rows))

        if rows:
            out.append(f"【上次压缩后的对话（最新 {len(rows)} 条）】")
        else:
            rows = conn.execute(
                'SELECT time, speaker, content FROM messages '
                'WHERE project IN (?, ?) ORDER BY id DESC LIMIT 30',
                (project, project_encoded)
            ).fetchall()
            rows = list(reversed(rows))
            out.append(f"【最近对话（最新 {len(rows)} 条）】")

        for r in rows:
            preview = r[2][:500].replace('\n', ' ')
            out.append(f"[{r[0]}] {r[1]}: {preview}")

        conn.close()
    except Exception as e:
        out.append(f"[对话种子读取失败: {e}]")

    out.append("")

    # -- 读 MEMORY.md（前120行）--
    memory_path = os.path.expanduser(
        f'~/.claude/projects/{project_encoded}/memory/MEMORY.md'
    )
    if os.path.exists(memory_path):
        try:
            with open(memory_path) as f:
                lines = f.readlines()
            out.append("【MEMORY（前120行）】")
            out.append(''.join(lines[:120]).rstrip())
        except Exception:
            pass
        out.append("")

    print('\n'.join(out))


if __name__ == '__main__':
    main()
