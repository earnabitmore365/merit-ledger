#!/usr/bin/env python3
"""
通讯部写入脚本 — 由 Claude Code Hooks 自动触发
处理 Stop 和 UserPromptSubmit 两个事件，写入 ~/.claude/conversations.db
+ daily md（新格式：悉尼 5AM 切日 + 纯对话 + jsonl 锚点 + 500 行滚动）
"""

import sys
import json
import sqlite3
import os
import re
import time
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

DB_PATH = os.path.expanduser('~/.claude/conversations.db')
TAIJI_DB_PATH = os.path.expanduser('~/.claude/conversations_taiji.db')
LOG_PATH = '/tmp/db_write.log'
TAIJI_PROJECT = '-Users-allenbot'

# daily md 新格式配置
SYDNEY_TZ = ZoneInfo('Australia/Sydney')
DAILY_ROLL_LINES = 500            # 超过 500 行滚动到下一个文件
DAILY_PAUSED_FLAG = os.path.expanduser('~/.claude/state/daily_write_paused')
CURSOR_PATH = os.path.expanduser('~/.claude/state/daily_write_cursor.json')
PROJECTS_BASE_DIR = os.path.expanduser('~/.claude/projects')


def log(msg):
    """轻量调试日志，写入 /tmp/db_write.log"""
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

# 标签词表（8类）
TAG_WORDS = {
    '流程':   ['初考', '专考', '组考', '照妖镜', '分班', '冠军', 'gate', '门槛', '成绩单', '淘汰'],
    '技术验证': ['回测', '种子', 'wf', 'mc', 'oos', 'walk-forward', 'monte carlo', '过拟合', '翻倍率', '爆仓率'],
    '市场状态': ['regime', '牛市', '熊市', '盘整', '初牛', '初熊', '已知事实', '叠加', '子阶段', 'intrabar'],
    '数据':   ['k线', '下载', 'sqlite', '数据库', '币本位', '合约', '周期'],
    '决策词':  ['拍板', '决定', '不用', '砍掉', '保留', '就这样', '就这么定了', '做吧', '批了'],
    '协作':   ['handoff', 'checkpoint', '方案', '报告', '压缩', '恢复'],
    '纠错':   ['不要这样', '不对', '错了', '你怎么', '干什么飞机', '你老是', '又忘了',
               '我不是叫你', '你先别', '没头没尾', '敷衍', '漏东西', '自审', '你赶时间吗'],
    '提升':   ['更细心', '可以更好', '主动一点', '应该主动', '不用我问', '不用我到', '本来应该',
               '你自己应该', '还可以', '做得更好', '没想到'],
    '策略币种': ['策略', 'vpt', 'meanreversion', 'demandindex', 'cci', 'trix', 'rsi', 'macd', 'bollinger',
               'sol', 'btc', 'eth', 'bnb', 'xrp', 'ada', 'avax', 'link', 'dot', 'trx'],
}

DECISION_WORDS = TAG_WORDS['决策词']

SKIP_DIRS = {
    '-Users-allenbot--claude',
    '-private-tmp-claude-evolver',
    '-Users-allenbot--openclaw-workspace',
}


# ═════════════════════════════════════════════════════
#  Daily MD 新格式 helpers (悉尼 5AM 切日 + 滚动文件 + 锚点)
# ═════════════════════════════════════════════════════

def get_daily_date(dt=None):
    """返回悉尼 5AM 切日的日期字符串 YYYY-MM-DD

    悉尼时间 05:00 是新一天的起点。04:59 归前一天。
    dt 可以是 UTC datetime 或任意带 tz 的 datetime；None 表示"现在"。
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    sydney = dt.astimezone(SYDNEY_TZ)
    if sydney.hour < 5:
        sydney = sydney - timedelta(days=1)
    return sydney.strftime('%Y-%m-%d')


_ROLL_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$')


def list_rolling_files(daily_dir, date_str):
    """返回当天所有滚动 md 文件的完整路径列表，按 roll index 升序

    base 文件 YYYY-MM-DD.md 视为 roll=1
    滚动文件 YYYY-MM-DD-002.md 是 roll=2，以此类推
    """
    if not os.path.isdir(daily_dir):
        return []
    results = []  # [(roll, full_path)]
    for entry in os.listdir(daily_dir):
        m = _ROLL_PATTERN.match(entry)
        if not m or m.group(1) != date_str:
            continue
        roll = int(m.group(2)) if m.group(2) else 1
        results.append((roll, os.path.join(daily_dir, entry)))
    results.sort(key=lambda x: x[0])
    return [p for _, p in results]


def get_latest_rolling_md(daily_dir, date_str):
    """返回当天最新的滚动 md 文件路径（空目录返回 base 路径）"""
    files = list_rolling_files(daily_dir, date_str)
    if not files:
        return os.path.join(daily_dir, f'{date_str}.md')
    return files[-1]


def get_next_rolling_md(daily_dir, date_str):
    """返回下一个滚动文件路径（用于当前 md 已满 DAILY_ROLL_LINES 时滚动）"""
    files = list_rolling_files(daily_dir, date_str)
    if not files:
        return os.path.join(daily_dir, f'{date_str}.md')
    latest_basename = os.path.basename(files[-1])
    m = _ROLL_PATTERN.match(latest_basename)
    latest_roll = int(m.group(2)) if m.group(2) else 1
    next_roll = latest_roll + 1
    return os.path.join(daily_dir, f'{date_str}-{next_roll:03d}.md')


def get_all_rolling_md_for_date(daily_dir, date_str):
    """给 reader（session_start 等）用：返回当天所有滚动文件路径，按 roll 升序"""
    return list_rolling_files(daily_dir, date_str)


def build_jsonl_anchor(transcript_path, line_start, line_end):
    """构建 jsonl 锚点 HTML 注释：<!-- jsonl: <rel_path>#L<s>-L<e> -->

    rel_path 相对 ~/.claude/projects/，如 "-Users-allenbot/abc-def.jsonl"
    """
    try:
        rel = os.path.relpath(transcript_path, PROJECTS_BASE_DIR)
    except Exception:
        rel = transcript_path
    return f'<!-- jsonl: {rel}#L{line_start}-L{line_end} -->'


# ═════════════════════════════════════════════════════
#  Cursor state (防止同一轮消息被 Stop hook 重复写入)
# ═════════════════════════════════════════════════════

def _read_cursor():
    """读整个 cursor dict {session_id: last_written_line_no}"""
    if not os.path.exists(CURSOR_PATH):
        return {}
    try:
        with open(CURSOR_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cursor(data):
    """原子写 cursor dict"""
    try:
        os.makedirs(os.path.dirname(CURSOR_PATH), exist_ok=True)
        tmp = CURSOR_PATH + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.rename(tmp, CURSOR_PATH)
    except Exception as e:
        log(f'cursor write error: {e}')


def get_session_cursor(session_id):
    """返回指定 session 的 last_written_line_no（默认 0）"""
    if not session_id:
        return 0
    data = _read_cursor()
    return int(data.get(session_id, 0))


def update_session_cursor(session_id, line_no):
    """把 session 的 last_written_line_no 更新为 line_no（只前进不后退）"""
    if not session_id:
        return
    data = _read_cursor()
    current = int(data.get(session_id, 0))
    if line_no > current:
        data[session_id] = line_no
        # 限制 dict 大小：超过 100 个 session 时丢弃最旧的
        if len(data) > 100:
            # 按 line_no 升序保留最新 80 个
            sorted_items = sorted(data.items(), key=lambda kv: kv[1], reverse=True)[:80]
            data = dict(sorted_items)
        _write_cursor(data)


# ═════════════════════════════════════════════════════
#  标签 + schema + speaker 映射
# ═════════════════════════════════════════════════════

def get_tags(speaker, content):
    """根据内容匹配词表，返回逗号分隔的 tags 字符串"""
    content_lower = content.lower()
    matched = set()
    for category, words in TAG_WORDS.items():
        if category == '决策词':
            continue
        for word in words:
            if word.lower() in content_lower:
                matched.add(word if not word.islower() else word)
    if speaker in ('无极', '执事'):
        for word in DECISION_WORDS:
            if word.lower() in content_lower:
                matched.add('决策')
                break
    return ','.join(sorted(matched)) if matched else ''


def ensure_schema(conn):
    """确保 DB 表结构存在（用于新建太极 DB）"""
    conn.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT, speaker TEXT, content TEXT,
        project TEXT, session_id TEXT,
        tags TEXT, reactions TEXT DEFAULT '{}'
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS stop_points (
        speaker TEXT, project TEXT, last_id INTEGER, stopped_at DATETIME,
        PRIMARY KEY (speaker, project)
    )''')
    conn.commit()


def remap_speaker_taiji(speaker):
    """太极上下文的 speaker 映射：opus=太极，sonnet=影太极"""
    if speaker == '白纱':
        return '太极'
    elif speaker == '黑丝':
        return '影太极'
    return speaker


def get_project_from_session(session_id):
    """通过 session_id 在 ~/.claude/projects/ 里找对应目录，返回 project 名或 None"""
    if not session_id:
        return None
    projects_dir = PROJECTS_BASE_DIR
    try:
        for proj_dir_name in os.listdir(projects_dir):
            proj_dir = os.path.join(projects_dir, proj_dir_name)
            if not os.path.isdir(proj_dir):
                continue
            try:
                for fname in os.listdir(proj_dir):
                    if fname.startswith(session_id) and fname.endswith('.jsonl'):
                        if proj_dir_name in SKIP_DIRS:
                            return None
                        return proj_dir_name
            except Exception:
                continue
    except Exception:
        pass
    return None


def parse_last_assistant(transcript_path):
    """读取 JSONL 末尾，收集最后一个 turn 的所有 assistant 内容（文字 + 工具调用摘要）

    此函数用于 DB 写入（保留工具摘要），与 daily md 生成解耦。
    """
    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
        tail = lines[-200:]

        parts = []
        speaker = None

        for line in reversed(tail):
            try:
                d = json.loads(line.strip())
                if d.get('type') == 'user':
                    break
                if d.get('type') != 'assistant':
                    continue
                msg = d.get('message', {})
                model = msg.get('model', '')
                if speaker is None:
                    speaker = '白纱' if 'opus' in model else ('黑丝' if 'sonnet' in model else '未知')
                blocks = msg.get('content', [])
                text_parts = []
                for b in blocks:
                    if not isinstance(b, dict):
                        continue
                    if b.get('type') == 'text' and b.get('text', '').strip():
                        text_parts.append(b['text'].strip())
                    elif b.get('type') == 'tool_use':
                        tool_name = b.get('name', '?')
                        tool_input = b.get('input', {})
                        hint = tool_input.get('file_path', '') or tool_input.get('command', '') or tool_input.get('pattern', '')
                        if hint:
                            hint = str(hint)[:80]
                            text_parts.append(f'[工具:{tool_name} → {hint}]')
                        else:
                            text_parts.append(f'[工具:{tool_name}]')
                text = '\n'.join(text_parts).strip()
                if text:
                    parts.append(text)
            except Exception:
                continue

        if parts:
            full_text = '\n\n'.join(reversed(parts)).strip()
            return speaker or '未知', full_text
    except Exception:
        pass
    return '未知', ''


DAILY_BASE = PROJECTS_BASE_DIR
DAILY_HOME = os.path.join(DAILY_BASE, '-Users-allenbot', 'memory', 'daily')
MISSION_PATH = os.path.expanduser('~/.claude/merit/mission.json')


def parse_last_turn_messages(transcript_path, is_taiji=False, after_line=0):
    """解析 JSONL 从 `after_line + 1` 开始到末尾的消息，返回结构化消息列表

    after_line=0 时退化为"从最后一个 user 消息开始读到末尾"（首次写入）
    after_line>0 时只读 line_no > after_line 的消息（增量写入，防重复）

    返回 [{speaker, text, timestamp, line_start, line_end}, ...]
    - 只保留有 text 的消息（剔除纯 tool_use 消息）
    - 剔除所有 tool_use 块，只留 text 块
    - line_start/line_end 是该条消息在 jsonl 中的物理行号（1-based）
    """
    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
        if not lines:
            return []

        if after_line > 0:
            # 增量模式：从 after_line 之后开始读
            start_idx = after_line  # lines[after_line] 是第 after_line+1 行（0-based）
        else:
            # 首次模式：找最后一个有效 user 消息的行号
            start_idx = None
            for i in range(len(lines) - 1, -1, -1):
                try:
                    obj = json.loads(lines[i])
                    if obj.get('type') == 'user':
                        content = obj.get('message', {}).get('content')
                        has_text = False
                        if isinstance(content, str) and content.strip():
                            has_text = True
                        elif isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get('type') == 'text' and block.get('text', '').strip():
                                    has_text = True
                                    break
                        if has_text:
                            start_idx = i
                            break
                except Exception:
                    continue

            if start_idx is None:
                return []

        messages = []
        for idx in range(start_idx, len(lines)):
            raw_line = lines[idx]
            try:
                obj = json.loads(raw_line)
            except Exception:
                continue
            line_no = idx + 1  # 1-based
            msg_type = obj.get('type', '')
            timestamp = obj.get('timestamp', '')

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
                    # 太极项目=无极，两仪项目=执事
                    speaker = '无极' if is_taiji else '执事'
                    messages.append({
                        'speaker': speaker,
                        'text': text,
                        'timestamp': timestamp,
                        'line_start': line_no,
                        'line_end': line_no,
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
                        'timestamp': timestamp,
                        'line_start': line_no,
                        'line_end': line_no,
                    })

        return messages
    except Exception:
        return []


def format_message_block(msg, transcript_path):
    """把一条消息格式化为 markdown block

    ## HH:MM:SS | speaker
    <!-- jsonl: <rel_path>#L<s>-L<e> -->

    text content

    ---
    """
    ts = msg.get('timestamp', '')
    time_label = ''
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            sydney_dt = dt.astimezone(SYDNEY_TZ)
            time_label = sydney_dt.strftime('%H:%M:%S')
        except Exception:
            time_label = ts[:19]
    if not time_label:
        time_label = datetime.now(SYDNEY_TZ).strftime('%H:%M:%S')

    anchor = build_jsonl_anchor(transcript_path, msg['line_start'], msg['line_end'])
    return (
        f"## {time_label} | {msg['speaker']}\n"
        f"{anchor}\n\n"
        f"{msg['text']}\n\n"
        f"---\n"
    )


def write_daily_md(session_id, transcript_path, project):
    """追加最后一轮对话到当天 daily md（新格式）

    - 时区：悉尼 5AM 切日
    - 内容：只保留 user.text + assistant.text，剔除 tool_use
    - 锚点：每条消息附 <!-- jsonl: rel_path#L<s>-L<e> -->
    - 滚动：超过 DAILY_ROLL_LINES 行写到 YYYY-MM-DD-002.md
    - 禁用开关：~/.claude/state/daily_write_paused 存在时跳过
    """
    # 禁用开关（Mission B 原子切换期间触发）
    if os.path.exists(DAILY_PAUSED_FLAG):
        log('daily write paused, skipping')
        return

    try:
        # 按项目分目录
        if project and project != '太极':
            daily_dir = os.path.join(DAILY_BASE, project, 'memory', 'daily')
        else:
            daily_dir = DAILY_HOME
        os.makedirs(daily_dir, exist_ok=True)

        is_taiji = (project == '太极')
        # 读 cursor 按 session 隔离的 last_written_line_no，只写增量
        cursor = get_session_cursor(session_id)
        messages = parse_last_turn_messages(transcript_path, is_taiji=is_taiji, after_line=cursor)
        if not messages:
            return

        # 按消息的 timestamp 分日（一个 turn 通常跨不了 5AM 边界，保险起见按每条分组）
        # 简化：整轮按第一条 timestamp 归日
        first_ts = messages[0].get('timestamp', '')
        if first_ts:
            try:
                dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
                date_str = get_daily_date(dt)
            except Exception:
                date_str = get_daily_date()
        else:
            date_str = get_daily_date()

        # 构建完整 blocks 文本
        blocks_text = ''.join(format_message_block(m, transcript_path) for m in messages)

        # 选定目标文件（最新滚动 or 新滚动）
        target_path = get_latest_rolling_md(daily_dir, date_str)
        existing_line_count = 0
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as f:
                existing_line_count = sum(1 for _ in f)
        if existing_line_count >= DAILY_ROLL_LINES:
            # 滚动到下一个
            target_path = get_next_rolling_md(daily_dir, date_str)
            existing_line_count = 0

        # 新文件需要写文件头
        is_new_file = not os.path.exists(target_path)
        with open(target_path, 'a', encoding='utf-8') as f:
            if is_new_file:
                f.write(f"# {date_str} (Sydney AEST/AEDT)\n\n")
            f.write(blocks_text)

        # 更新 cursor：保证下次 Stop 不会重复写同一批消息
        max_line = max(m['line_end'] for m in messages)
        update_session_cursor(session_id, max_line)

        log(f'Daily md written: {target_path} +{len(messages)} msgs (cursor→{max_line})')
    except Exception as e:
        log(f'Daily md ERROR: {e}')


def write_message(conn, speaker, content, project, session_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tags = get_tags(speaker, content)
    cursor = conn.execute(
        'INSERT INTO messages (time, speaker, content, project, session_id, tags) VALUES (?, ?, ?, ?, ?, ?)',
        (now, speaker, content, project, session_id, tags)
    )
    conn.commit()
    return cursor.lastrowid


def upsert_stop_point(conn, speaker, project, last_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        '''INSERT INTO stop_points (speaker, project, last_id, stopped_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(speaker, project) DO UPDATE SET
               last_id=excluded.last_id,
               stopped_at=excluded.stopped_at''',
        (speaker, project, last_id, now)
    )
    conn.commit()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    event = data.get('hook_event_name', '')
    session_id = data.get('session_id', '')

    project = get_project_from_session(session_id)

    if project is None:
        if event == 'Stop':
            transcript_path = data.get('transcript_path', '')
            if transcript_path:
                write_daily_md(session_id, transcript_path, None)
        sys.exit(0)

    is_taiji = (project == TAIJI_PROJECT)
    db_path = TAIJI_DB_PATH if is_taiji else DB_PATH
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)

    agent_id = data.get('agent_id', '')
    agent_speaker_override = None
    if agent_id.startswith('baisha'):
        agent_speaker_override = '白纱'
        log(f'Subagent detected: agent_id={agent_id} → speaker=白纱')

    if event == 'Stop':
        transcript_path = data.get('transcript_path', '')
        log(f'Stop: session={session_id[:8]} project={project} taiji={is_taiji} transcript={transcript_path[-50:] if transcript_path else "EMPTY"}')

        write_daily_md(session_id, transcript_path, '太极' if is_taiji else project)

        speaker, content = '未知', ''
        for attempt in range(3):
            speaker, content = parse_last_assistant(transcript_path)
            if content:
                break
            if attempt < 2:
                time.sleep(0.5)
        if agent_speaker_override:
            speaker = agent_speaker_override
        if is_taiji:
            speaker = remap_speaker_taiji(speaker)
        log(f'Stop result: speaker={speaker} content_len={len(content)}')
        if content:
            last_id = write_message(conn, speaker, content, project, session_id)
            upsert_stop_point(conn, speaker, project, last_id)
            log(f'Stop written: id={last_id} db={"taiji" if is_taiji else "main"}')

    elif event == 'UserPromptSubmit':
        content = data.get('prompt', '').strip()
        if content:
            if is_taiji:
                user_speaker = '无极'
            elif project.lower() in ('miao', '-users-allenbot-projects-miao'):
                user_speaker = '老祖'
            else:
                user_speaker = '执事'
            write_message(conn, user_speaker, content, project, session_id)

    elif event == 'PreCompact':
        transcript_path = data.get('transcript_path', '')
        speaker, content = parse_last_assistant(transcript_path)
        if is_taiji:
            speaker = remap_speaker_taiji(speaker)
        last_id = write_message(conn, '系统', f'[压缩点] {session_id[:8]}', project, session_id)
        if speaker and speaker not in ('未知',):
            upsert_stop_point(conn, speaker, project, last_id)

    elif event == 'SessionEnd':
        transcript_path = data.get('transcript_path', '')
        reason = data.get('reason', 'other')
        speaker, content = parse_last_assistant(transcript_path)
        if is_taiji:
            speaker = remap_speaker_taiji(speaker)
        last_id = write_message(conn, '系统', f'[会话结束:{reason}] {session_id[:8]}', project, session_id)
        if speaker and speaker not in ('未知',):
            upsert_stop_point(conn, speaker, project, last_id)

    conn.close()


if __name__ == '__main__':
    main()
