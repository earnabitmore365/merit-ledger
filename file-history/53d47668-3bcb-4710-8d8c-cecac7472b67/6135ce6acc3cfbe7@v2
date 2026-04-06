#!/usr/bin/env python3
"""
记忆系统端到端测试 — 永久保留，verify.py 调用

跑法：python3 test_memory.py
输出：N/10 通过
"""

import os
import sqlite3
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
MERIT_DIR = os.path.expanduser("~/.claude/merit")
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, MERIT_DIR)

PASSED = 0
FAILED = 0


def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✅ {PASSED + FAILED:2d}/10 {name}")
    else:
        FAILED += 1
        print(f"  ❌ {PASSED + FAILED:2d}/10 {name}: {detail}")


def main():
    print("═══ test_memory.py — 记忆系统端到端测试 ═══\n")

    # 1. db_write TAIJI_PROJECT
    from db_write import TAIJI_PROJECT
    test("TAIJI_PROJECT 常量", TAIJI_PROJECT == "-Users-allenbot", f"实际: {TAIJI_PROJECT}")

    # 2. db_write SKIP_DIRS 不含太极
    from db_write import SKIP_DIRS
    test("SKIP_DIRS 不含太极", "-Users-allenbot" not in SKIP_DIRS, f"还在: {SKIP_DIRS}")

    # 3. db_write ensure_schema 建表
    from db_write import ensure_schema
    test_db = "/tmp/test_memory_schema.db"
    try:
        conn = sqlite3.connect(test_db)
        ensure_schema(conn)
        tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        os.remove(test_db)
        test("ensure_schema 建表", "messages" in tables and "stop_points" in tables, f"tables: {tables}")
    except Exception as e:
        test("ensure_schema 建表", False, str(e))

    # 4. db_write remap_speaker_taiji
    from db_write import remap_speaker_taiji
    test("remap_speaker 白纱→太极",
         remap_speaker_taiji("白纱") == "太极" and remap_speaker_taiji("黑丝") == "影太极",
         f"白纱→{remap_speaker_taiji('白纱')}, 黑丝→{remap_speaker_taiji('黑丝')}")

    # 5. db_write get_tags
    from db_write import get_tags
    tags = get_tags("白纱", "我们做了回测验证")
    test("get_tags 标签匹配", "回测" in tags, f"tags: {tags}")

    # 6. session_start _get_level 从 merit_gate 导入（500分制：250=金丹）
    from session_start import _get_level
    lv, title = _get_level(250)
    test("_get_level 250→金丹", title == "金丹", f"实际: {title}")

    # 7. session_start inject_rules 不崩
    try:
        from session_start import inject_rules
        # 用一个不存在的 cwd，不应该崩
        inject_rules("/tmp/nonexistent")
        test("inject_rules 不崩", True)
    except Exception as e:
        test("inject_rules 不崩", False, str(e))

    # 8. daily_digest basic_tags
    from daily_digest import basic_tags
    tags = basic_tags("石卫拦截了一个bug修复操作")
    test("basic_tags 关键词", len(tags) > 0, f"tags: {tags}")

    # 9. daily_digest run_evolve 可调用
    from daily_digest import run_evolve
    test("run_evolve 函数存在", callable(run_evolve))

    # 10. pre_compact extract_text_from_content
    from pre_compact_save import extract_text_from_content
    r1 = extract_text_from_content("hello world")
    r2 = extract_text_from_content([{"type": "text", "text": "test msg"}])
    test("extract_text_from_content",
         r1 == "hello world" and "test msg" in r2,
         f"str→{r1}, list→{r2}")

    print(f"\n{'═' * 40}")
    print(f"结果: {PASSED}/{PASSED + FAILED} 通过")
    if FAILED > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
