#!/usr/bin/env python3
"""暗哨 v2 — 5 维度巡查，结果写 patrol_report.json，异常 ping 太极（不是白纱）

用法：
    python3 ~/.claude/scripts/anshao_patrol.py          # 巡查
    python3 ~/.claude/scripts/anshao_patrol.py --reset   # 清除收工标记

launchd 每 10 分钟自动运行（com.wuji.anshao.plist）

v2 改动（2026-04-13 执事方案）：
- 5 维度：活动 / 石卫违规 / mission状态 / verify健康 / 积分趋势
- 异常 ping 太极（8788），不 ping 白纱——暗哨给太极汇报
- 输出 patrol_report.json 供太极读取
- 保留 v1 收工感知（SHOUGONG_FLAG）
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime

# ══════════════════════════════════════════
#  配置
# ══════════════════════════════════════════

MERIT_DIR = os.path.expanduser("~/.claude/merit")

# wuji-auto-trading 项目路径（动态查找）
WUJI_ROOT = os.path.join(os.path.expanduser("~"), "project", "wuji-auto-trading")
if not os.path.isdir(WUJI_ROOT):
    for vol in ("/Volumes/SSD-2TB", "/Volumes/SSD-1TB"):
        alt = os.path.join(vol, "project", "wuji-auto-trading")
        if os.path.isdir(alt):
            WUJI_ROOT = alt
            break

CHANNEL_TOKEN_PATH = os.path.expanduser("~/.claude/channel-server/.channel_token")
TAIJI_PORT = 8788       # 暗哨 → 太极（v2: 给太极汇报，不给白纱）
TIMEOUT_MIN = 30
SHOUGONG_FLAG = os.path.join(MERIT_DIR, "baisha_shougong.flag")
REPORT_PATH = os.path.join(MERIT_DIR, "patrol_report.json")

# ══════════════════════════════════════════
#  5 维度检查
# ══════════════════════════════════════════


def check_activity():
    """维度1: wuji-auto-trading 下最近修改的 .py 的 mtime"""
    latest_mtime = 0
    latest_file = ""
    for dirpath, dirs, files in os.walk(WUJI_ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(dirpath, f)
                mt = os.path.getmtime(fp)
                if mt > latest_mtime:
                    latest_mtime = mt
                    latest_file = fp
    if latest_mtime == 0:
        return {"ok": False, "age_min": 999, "detail": "无 .py 文件"}
    age_min = int((time.time() - latest_mtime) / 60)
    ok = age_min < TIMEOUT_MIN
    return {"ok": ok, "age_min": age_min, "latest": os.path.basename(latest_file)}


def check_violations():
    """维度2: 读 shiwei_log/今天.md，grep 最近 10 分钟的两仪 DENY"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(MERIT_DIR, "shiwei_log", f"{today}.md")
    if not os.path.exists(log_path):
        return {"ok": True, "recent_deny": 0, "detail": "无今日日志"}
    try:
        cutoff = time.time() - 600  # 10 分钟内
        deny_count = 0
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                if "两仪" in line and "DENY" in line:
                    deny_count += 1
        return {"ok": deny_count == 0, "recent_deny": deny_count}
    except Exception:
        return {"ok": True, "recent_deny": 0, "detail": "读取失败"}


def check_mission():
    """维度3: 读 mission*.json 找两仪 active mission"""
    import glob
    for p in glob.glob(os.path.join(MERIT_DIR, "mission*.json")):
        try:
            with open(p) as f:
                m = json.load(f)
            if m.get("agent") == "两仪" and m.get("status") == "active":
                return {"ok": True, "status": "active", "mission": m.get("mission", "?")}
        except Exception:
            continue
    return {"ok": False, "status": "none", "detail": "无活跃 mission"}


def check_verify():
    """维度4: 读 scan_stats.json 的 hits"""
    stats_path = os.path.join(MERIT_DIR, "scan_stats.json")
    if not os.path.exists(stats_path):
        return {"ok": True, "hits": 0, "detail": "无 scan_stats"}
    try:
        with open(stats_path) as f:
            stats = json.load(f)
        hits = stats.get("hits", 0)
        return {"ok": hits == 0, "hits": hits}
    except Exception:
        return {"ok": True, "hits": 0, "detail": "读取失败"}


def check_credit_trend():
    """维度5: 读 credit.json 两仪最近 5 条 history"""
    try:
        with open(os.path.join(MERIT_DIR, "credit.json")) as f:
            data = json.load(f)
        history = data.get("history", [])
        # 过滤两仪的记录，取最近 5 条
        liangyi_hist = [h for h in history if h.get("agent") == "两仪"][-5:]
        if not liangyi_hist:
            return {"ok": True, "recent_deltas": [], "detail": "无历史"}
        deltas = [h.get("delta", 0) for h in liangyi_hist]
        # 连续 3+ 条负数 = 异常
        consecutive_neg = 0
        for d in reversed(deltas):
            if d < 0:
                consecutive_neg += 1
            else:
                break
        ok = consecutive_neg < 3
        return {"ok": ok, "recent_deltas": deltas, "consecutive_neg": consecutive_neg}
    except Exception:
        return {"ok": True, "recent_deltas": [], "detail": "读取失败"}


# ══════════════════════════════════════════
#  收工感知（v1 保留）
# ══════════════════════════════════════════


def is_shougong():
    return os.path.exists(SHOUGONG_FLAG)


def clear_shougong():
    if os.path.exists(SHOUGONG_FLAG):
        os.remove(SHOUGONG_FLAG)
        print("✅ 收工标记已清除")
    else:
        print("ℹ️ 无收工标记")


# ══════════════════════════════════════════
#  输出 + ping
# ══════════════════════════════════════════


def send_ping_taiji(msg):
    """异常时 ping 太极（8788），不 ping 白纱"""
    try:
        with open(CHANNEL_TOKEN_PATH) as f:
            token = f.read().strip()
        subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{TAIJI_PORT}",
             "-H", f"Authorization: Bearer {token}",
             "-d", msg],
            capture_output=True, timeout=10
        )
    except Exception:
        pass


def write_report(status, checks, message):
    report = {
        "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "status": status,
        "checks": checks,
        "message": message,
    }
    try:
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return report


# ══════════════════════════════════════════
#  主逻辑
# ══════════════════════════════════════════


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        clear_shougong()
        return

    # 收工检查
    if is_shougong():
        print("📡 暗哨巡查：🏁 白纱已收工，不巡查")
        write_report("shougong", {}, "白纱已收工")
        return

    # 5 维度检查
    checks = {
        "activity": check_activity(),
        "violations": check_violations(),
        "mission": check_mission(),
        "verify": check_verify(),
        "credit_trend": check_credit_trend(),
    }

    # 统计异常数
    yellow_count = sum(1 for c in checks.values() if not c.get("ok", True))

    # 分级
    if yellow_count == 0:
        status = "normal"
        message = "5 维度全绿，正常运行中"
    elif yellow_count <= 2:
        status = "warning"
        failed = [k for k, v in checks.items() if not v.get("ok", True)]
        message = f"异常 {yellow_count} 项：{', '.join(failed)}"
    else:
        status = "critical"
        failed = [k for k, v in checks.items() if not v.get("ok", True)]
        message = f"严重：{yellow_count} 项异常：{', '.join(failed)}"

    # 输出
    print(f"📡 暗哨巡查 [{status.upper()}]")
    for dim, result in checks.items():
        icon = "✅" if result.get("ok", True) else "⚠️"
        print(f"  {icon} {dim}: {json.dumps(result, ensure_ascii=False)}")
    print(f"  → {message}")

    # 写报告
    write_report(status, checks, message)

    # ping 太极（异常才发）
    if status in ("warning", "critical"):
        send_ping_taiji(f"暗哨巡查 [{status}]: {message}")


if __name__ == "__main__":
    main()
