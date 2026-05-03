#!/opt/homebrew/bin/python3.11
"""
Wuji Ops MCP — Vultr 服务器统一运维工具

工具清单（共 12 个）：
  vultr_deploy(files, restart)              → rsync 指定文件 + 可选重启 gateway
  vultr_status()                            → CPU/内存/磁盘/进程/uptime 一览
  vultr_logs(service, lines)               → 查日志（gateway / journal / monitor）
  vultr_service(action, svc)               → start/stop/restart/reload/status
  vultr_health()                            → 业务层健康检查
  vultr_crontab()                           → 查看/验证 crontab
  vultr_wipe()                              → 清除所有 wuji 部署（⚠️ 不可逆）
  vultr_ls(path)                            → 查目录/文件（限 VULTR_ROOT 下）
  vultr_cat(path, lines)                   → 看文件内容（.env 自动屏蔽值）
  vultr_pip_check(packages)                → 检查 Python 包是否已装
  vultr_env_check()                         → 查 .env KEY 列表（不显示值）
  vultr_investigate(time_aest, window_minutes, verbose) → 断线事件排查（时区换算+日志分析+模式标签）
"""

import os
import posixpath
import re
import shlex
import subprocess
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

# ==================== 连接配置 ====================

VULTR_HOST = "root@45.76.199.244"
VULTR_KEY  = "/Users/allenbot/.ssh/id_ed25519"
VULTR_ROOT = "/opt/wuji-auto-trading"
LOCAL_ROOT = "/Volumes/SSD-2TB/project/wuji-auto-trading"
GATEWAY_SERVICE = "wuji-gateway"

# ==================== SSH 工具函数 ====================

def _ssh(cmd: str, timeout: int = 30) -> str:
    """在 Vultr 上执行命令，返回 stdout + stderr 合并输出。"""
    try:
        result = subprocess.run(
            ["ssh", "-i", VULTR_KEY,
             "-o", "ConnectTimeout=10",
             "-o", "StrictHostKeyChecking=yes",
             VULTR_HOST, cmd],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        def _decode(s) -> str:
            return (s.decode() if isinstance(s, bytes) else (s or "")).strip()
        partial_out = _decode(e.stdout)
        partial_err = _decode(e.stderr)
        msg = f"[timeout after {timeout}s]"
        if partial_out:
            msg += f"\n--- stdout ---\n{partial_out}"
        if partial_err:
            msg += f"\n--- stderr ---\n{partial_err}"
        return msg
    except (FileNotFoundError, OSError) as e:
        return f"[ssh 启动失败] {type(e).__name__}: {e}"

    out = result.stdout.strip()
    err = result.stderr.strip()
    if result.returncode != 0 and err:
        return f"[exit {result.returncode}]\n{out}\n{err}".strip()
    return out or "(无输出)"


def _rsync(local_paths: list[str], timeout: int = 60) -> str:
    """将本地文件 rsync 到 Vultr，保留目录结构。"""
    if not local_paths:
        local_paths = [f"{LOCAL_ROOT}/src/"]

    results = []
    for local_path in local_paths:
        if local_path.endswith("/"):
            # 目录同步：用 --delete 保持远端与本地一致
            rel = os.path.relpath(local_path.rstrip("/"), LOCAL_ROOT)
            dest = f"{VULTR_HOST}:{VULTR_ROOT}/{rel}/"
            extra_flags = ["--delete"]
        else:
            # 单文件同步：不用 --delete（否则会清空目标目录）
            rel = os.path.relpath(local_path, LOCAL_ROOT)
            dest_rel_dir = os.path.dirname(rel)
            dest = f"{VULTR_HOST}:{VULTR_ROOT}/{dest_rel_dir}/" if dest_rel_dir else f"{VULTR_HOST}:{VULTR_ROOT}/"
            extra_flags = []

        result = subprocess.run(
            ["rsync", "-avz"] + extra_flags + [
                "-e", f"ssh -i {VULTR_KEY} -o StrictHostKeyChecking=yes",
                local_path, dest,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0:
            results.append(f"✅ rsync {os.path.basename(local_path.rstrip('/'))} OK")
        else:
            results.append(f"❌ rsync {local_path} 失败:\n{result.stderr.strip()}")

    return "\n".join(results)


def _safe_path(path: str) -> str | None:
    """
    验证路径在 VULTR_ROOT 下，防止路径穿越。
    接受相对路径（基于 VULTR_ROOT）或绝对路径。
    返回规范化的绝对路径，路径不合法则返回 None。
    """
    if not path.startswith("/"):
        path = posixpath.join(VULTR_ROOT, path)
    norm = posixpath.normpath(path)
    if not norm.startswith(VULTR_ROOT + "/") and norm != VULTR_ROOT:
        return None
    return norm


# ==================== MCP Server ====================

mcp = FastMCP("wuji-ops")


@mcp.tool()
def vultr_deploy(files: list[str] = None, restart: bool = True) -> str:
    """
    同步代码到 Vultr，可选重启 gateway service。

    files:   本地文件/目录列表（相对于项目根目录，如 ["src/data/feed_gateway.py"]）。
             不传则默认同步整个 src/ 目录。
    restart: 是否在同步后重启 gateway（默认 True）。
             首次部署时 service 文件还未创建，传 restart=False 跳过重启。
    """
    if files is None:
        files = []

    abs_paths = []
    for f in files:
        if os.path.isabs(f):
            if not (f.startswith(LOCAL_ROOT + "/") or f == LOCAL_ROOT):
                return f"❌ 路径不在项目目录下：{f}（仅允许 {LOCAL_ROOT} 下的路径）"
            abs_paths.append(f)
        else:
            abs_paths.append(os.path.join(LOCAL_ROOT, f))

    if not abs_paths:
        abs_paths = [f"{LOCAL_ROOT}/src/"]

    sync_result = _rsync(abs_paths)

    if restart:
        restart_result = _ssh(
            f"systemctl restart {GATEWAY_SERVICE} && sleep 2 && systemctl is-active {GATEWAY_SERVICE}"
        )
        return f"=== rsync ===\n{sync_result}\n\n=== 重启 {GATEWAY_SERVICE} ===\n{restart_result}"
    else:
        return f"=== rsync ===\n{sync_result}\n\n=== 重启 ===\n跳过（restart=False）"


@mcp.tool()
def vultr_status() -> str:
    """
    查看 Vultr 服务器状态：CPU、内存、磁盘、uptime、关键进程。
    """
    cmd = """
echo '=== Uptime ===' && uptime
echo '=== CPU/内存 ===' && free -h && echo '' && top -bn1 | head -5
echo '=== 磁盘 ===' && df -h /
echo '=== 关键进程 ===' && ps aux --sort=-%cpu | grep -E 'python3|feed_gateway|wuji' | grep -v grep | head -10
echo '=== systemd wuji 服务 ===' && systemctl list-units --type=service | grep wuji || echo '无 wuji 服务'
""".strip()
    return _ssh(cmd, timeout=20)


@mcp.tool()
def vultr_logs(service: str = "gateway", lines: int = 50) -> str:
    """
    查看 Vultr 上的日志。

    service: "gateway"（默认）→ gateway.log 文件
             "journal"       → journalctl -u wuji-gateway
             "monitor"       → gateway_monitor.log
    lines: 返回最后 N 行（默认 50）
    """
    lines = min(max(1, lines), 500)
    if service == "gateway":
        cmd = f"tail -n {lines} {VULTR_ROOT}/logs/gateway.log 2>/dev/null || echo '日志文件不存在'"
    elif service == "journal":
        cmd = f"journalctl -u {GATEWAY_SERVICE} -n {lines} --no-pager 2>/dev/null || echo 'journalctl 失败'"
    elif service == "monitor":
        cmd = f"tail -n {lines} {VULTR_ROOT}/logs/gateway_monitor.log 2>/dev/null || echo '日志文件不存在'"
    else:
        return f"未知 service: {service}（可选：gateway / journal / monitor）"

    return _ssh(cmd, timeout=15)


@mcp.tool()
def vultr_service(action: str, service: str = "wuji-gateway") -> str:
    """
    管理 Vultr 上的 systemd 服务。

    action: start    → 启动服务
            stop     → 停止服务
            restart  → 重启服务
            reload   → daemon-reload（重载 systemd 配置，改了 .service 文件后用）
            status   → 查看服务详细状态
    service: 服务名（默认 wuji-gateway）。action=reload 时忽略此参数。
    """
    allowed = {"start", "stop", "restart", "reload", "status"}
    if action not in allowed:
        return f"未知 action: {action}（可选：start / stop / restart / reload / status）"

    unit_re = re.compile(r'^[A-Za-z0-9:_.\-]+(\.(service|socket|timer|target))?$')
    if not unit_re.match(service):
        return f"❌ 非法服务名：{service}"
    svc_q = shlex.quote(service)

    if action == "reload":
        cmd = "systemctl daemon-reload && echo 'daemon-reload OK'"
    elif action == "status":
        cmd = f"systemctl status {svc_q} --no-pager | head -30"
    else:
        cmd = f"systemctl {action} {svc_q} && sleep 2 && systemctl is-active {svc_q}"

    return _ssh(cmd)


@mcp.tool()
def vultr_health() -> str:
    """
    业务层健康检查：
    - wuji-gateway systemd 状态
    - feed_gateway.py 进程是否在跑
    - ZMQ PUB/REP 端口（5555/5556）是否监听
    - 最新日志时间（行情最后更新）
    - 最近错误日志（最后 5 条 ERROR/WARNING）
    """
    cmd = f"""
echo '=== systemd 状态 ===' && systemctl is-active {GATEWAY_SERVICE} 2>/dev/null || echo inactive
echo '=== 进程 ===' && ps aux | grep 'feed_gateway' | grep -v grep | awk '{{print $1,$2,$3,$4,$11,$12}}' || echo '无进程'
echo '=== ZMQ 端口 ===' && ss -tlnp 2>/dev/null | grep -E '5555|5556' || echo '端口未监听'
echo '=== 日志最后1行 ===' && tail -n 1 {VULTR_ROOT}/logs/gateway.log 2>/dev/null || echo '无日志'
echo '=== 最近错误 ===' && grep -E 'ERROR|WARNING|CRITICAL' {VULTR_ROOT}/logs/gateway.log 2>/dev/null | tail -5 || echo '无错误记录'
""".strip()
    return _ssh(cmd, timeout=15)


@mcp.tool()
def vultr_crontab() -> str:
    """
    查看 Vultr 上的 crontab（root + 系统级），验证有无危险项。
    """
    cmd = """
echo '=== root crontab ===' && crontab -l 2>/dev/null || echo '（空）'
echo '=== /etc/cron.d/ ===' && ls /etc/cron.d/ 2>/dev/null && for f in /etc/cron.d/*; do echo "--- $f ---"; cat "$f" 2>/dev/null; done
echo '=== /etc/crontab ===' && cat /etc/crontab 2>/dev/null || echo '（无）'
""".strip()
    return _ssh(cmd, timeout=15)


@mcp.tool()
def vultr_ls(path: str = "") -> str:
    """
    查看 Vultr 服务器上的目录或文件列表。

    path: 相对于项目根目录的路径（如 "logs"、"src/data"），
          或以 /opt/wuji-auto-trading 开头的绝对路径。
          不传则列出项目根目录。
    """
    if not path:
        safe = VULTR_ROOT
    else:
        safe = _safe_path(path)
        if safe is None:
            return f"❌ 路径不在项目目录下：{path}（仅允许 {VULTR_ROOT} 下的路径）"

    cmd = f"ls -la {shlex.quote(safe)} 2>/dev/null || echo '路径不存在'"
    return _ssh(cmd, timeout=10)


@mcp.tool()
def vultr_cat(path: str, lines: int = 100) -> str:
    """
    查看 Vultr 服务器上的文件内容。

    path: 相对于项目根目录的路径（如 "logs/gateway.log"），
          或以 /opt/wuji-auto-trading 开头的绝对路径。
    lines: 返回最后 N 行（默认 100，上限 500）。

    注意：.env 文件自动屏蔽值，只显示 KEY=***。
    """
    safe = _safe_path(path)
    if safe is None:
        return f"❌ 路径不在项目目录下：{path}（仅允许 {VULTR_ROOT} 下的路径）"

    lines = min(max(1, lines), 500)

    if safe.endswith(".env"):
        cmd = f"grep -v '^#' {shlex.quote(safe)} 2>/dev/null | grep -v '^$' | sed 's/=.*/=***/' || echo '文件不存在或为空'"
    else:
        cmd = f"tail -n {lines} {shlex.quote(safe)} 2>/dev/null || echo '文件不存在'"

    return _ssh(cmd, timeout=15)


@mcp.tool()
def vultr_pip_check(packages: list[str]) -> str:
    """
    检查 Vultr 上 Python 包是否已安装。

    packages: 包名列表（如 ["zmq", "numpy", "hyperliquid"]）。
    """
    if not packages:
        return "请提供至少一个包名"

    name_re = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._\-\[\]]*$')
    bad = [p for p in packages if not name_re.match(p)]
    if bad:
        return f"❌ 非法包名：{bad}（仅允许字母/数字/ . _ - [ ]）"

    checks = " && ".join(
        f"echo '--- {pkg} ---' && (pip3 show {shlex.quote(pkg)} 2>/dev/null | grep -E '^(Name|Version):' || echo 'NOT INSTALLED')"
        for pkg in packages
    )
    return _ssh(checks, timeout=20)


@mcp.tool()
def vultr_env_check() -> str:
    """
    查看 Vultr 上 .env 文件的 KEY 列表（不显示任何值）。
    """
    cmd = (
        f"grep -v '^#' {VULTR_ROOT}/.env 2>/dev/null | grep -v '^$' | cut -d= -f1 "
        f"|| echo '.env 文件不存在'"
    )
    return _ssh(cmd, timeout=10)


@mcp.tool()
def vultr_wipe() -> str:
    """
    清除 Vultr 上所有 wuji 交易系统部署痕迹。

    执行顺序：
    1. 停止并禁用 wuji-gateway systemd 服务
    2. 删除 systemd 服务文件 + daemon-reload
    3. 删除项目目录 /opt/wuji-auto-trading/
    4. 删除 logrotate 配置 /etc/logrotate.d/wuji

    ⚠️ 不可逆操作，执行前请确认。
    """
    cmd = """
echo '=== 1. 停止并禁用服务 ===' \
  && systemctl stop wuji-gateway 2>/dev/null && echo 'stop OK' || echo 'stop: 服务不存在或已停止' \
  && systemctl disable wuji-gateway 2>/dev/null && echo 'disable OK' || echo 'disable: 服务不存在'

echo '=== 2. 删除 systemd 服务文件 ===' \
  && rm -f /etc/systemd/system/wuji-gateway.service && echo 'service file removed' \
  && systemctl daemon-reload && echo 'daemon-reload OK'

echo '=== 3. 删除项目目录 ===' \
  && rm -rf /opt/wuji-auto-trading/ && echo '/opt/wuji-auto-trading/ removed'

echo '=== 4. 删除 logrotate 配置 ===' \
  && rm -f /etc/logrotate.d/wuji && echo 'logrotate config removed'

echo '=== 完成 ==='
""".strip()
    return _ssh(cmd, timeout=60)


@mcp.tool()
def vultr_investigate(
    time_aest: str,
    window_minutes: int = 120,
    verbose: bool = False,
) -> str:
    """
    排查 gateway 断线事件，自动化日志分析 + 模式识别。

    time_aest:      事件时间（Australia/Sydney 本地时间，格式 "YYYY-MM-DD HH:MM"）。
                    DST（夏/冬令时）自动判定，输出里会显示实际 offset。
    window_minutes: 查询时间窗口，以 time_aest 为中心前后各取一半（默认 120 分钟）。
    verbose:        True 时附完整窗口内日志（默认 False，只输出关键行）。

    输出分四段：
      1. 摘要：断线次数、429 次数、并发重连检测
      2. 模式标签（PATTERN_*）：客观事实，不下根因结论
      3. 关键事件原始行（过滤 connect/disconnect/429/ERROR 等）
      4. BitMEX status 人工核对链接
    """
    if not (1 <= window_minutes <= 1440):
        return f"❌ window_minutes 超出范围（1-1440），当前值：{window_minutes}"

    # --- 1. 时区换算 ---
    sydney_tz = ZoneInfo("Australia/Sydney")
    try:
        local_dt = datetime.strptime(time_aest, "%Y-%m-%d %H:%M").replace(tzinfo=sydney_tz)
    except ValueError:
        return f"❌ 时间格式错误：{time_aest}（正确格式：YYYY-MM-DD HH:MM）"

    utc_dt = local_dt.astimezone(timezone.utc)
    offset_hours = int(local_dt.utcoffset().total_seconds()) // 3600
    tz_label = "AEDT" if offset_hours == 11 else "AEST"

    half = timedelta(minutes=window_minutes // 2)
    t_start = utc_dt - half
    t_end   = utc_dt + half
    t_start_str = t_start.strftime("%Y-%m-%d %H:%M:%S")
    t_end_str   = t_end.strftime("%Y-%m-%d %H:%M:%S")

    # DST 边界提示（4 月或 10 月）
    dst_warning = ""
    if local_dt.month in (3, 4, 10):
        dst_warning = "  ⚠️  当前日期接近 DST 切换边界，请确认 offset 是否正确\n"

    header = (
        f"=== vultr_investigate ===\n"
        f"输入：{time_aest} Australia/Sydney ({tz_label}, UTC{offset_hours:+d})\n"
        f"{dst_warning}"
        f"UTC 中心：{utc_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"查询窗口：{t_start_str} ~ {t_end_str} UTC（{window_minutes} 分钟）\n"
    )

    # --- 2. 拉日志（journalctl --since/--until，UTC 时间直接用） ---
    journal_cmd = (
        f"journalctl -u wuji-gateway "
        f"--since {shlex.quote(t_start_str)} --until {shlex.quote(t_end_str)} "
        f"--no-pager --output=short-iso 2>/dev/null | grep -v '^-- '"
    )
    raw_logs = _ssh(journal_cmd, timeout=30)

    if not raw_logs or raw_logs == "(无输出)":
        return header + "\n[日志] 该时间窗口内无日志记录。\n"

    lines = raw_logs.splitlines()
    total_lines = len(lines)

    # --- 3. 关键行提取 ---
    key_re = re.compile(
        r'disconnect|reconnect|websocket.*clos|closed.*websocket'
        r'|HTTP 429|429 Too Many|rate.?limit'
        r'|ERROR|CRITICAL|WARNING'
        r'|connect(?:ed|ing)?',
        re.IGNORECASE,
    )
    key_lines = [line for line in lines if key_re.search(line)]

    # --- 4. 统计 ---
    ts_re = re.compile(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})')

    disconnect_count = sum(1 for line in lines if re.search(r'disconnect|websocket.*clos|closed.*websocket', line, re.IGNORECASE))
    connect_count    = sum(1 for line in lines if re.search(r'connected|reconnect', line, re.IGNORECASE))
    rate_limit_count = sum(1 for line in lines if re.search(r'429|rate.?limit', line, re.IGNORECASE))

    # 并发重连：同一秒出现 ≥2 条 connect/disconnect 事件
    ts_event_counts: dict[str, int] = {}
    for line in lines:
        if re.search(r'connect|disconnect', line, re.IGNORECASE):
            m = ts_re.search(line)
            if m:
                ts = m.group(1)[:19]
                ts_event_counts[ts] = ts_event_counts.get(ts, 0) + 1
    concurrent_seconds = {ts: cnt for ts, cnt in ts_event_counts.items() if cnt >= 2}

    # 关键事件跨越时长（用于 EXTENDED_OUTAGE 判断）
    outage_span_secs = 0
    if key_lines:
        m0 = ts_re.search(key_lines[0])
        m1 = ts_re.search(key_lines[-1])
        if m0 and m1:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S" if "T" in m0.group(1) else "%Y-%m-%d %H:%M:%S"
                t0 = datetime.strptime(m0.group(1)[:19], fmt)
                t1 = datetime.strptime(m1.group(1)[:19], fmt)
                outage_span_secs = int((t1 - t0).total_seconds())
            except Exception:
                pass

    # --- 5. PATTERN 标签 ---
    patterns = []
    if rate_limit_count >= 1:
        patterns.append(f"PATTERN_429            — HTTP 429 出现 {rate_limit_count} 次")
    if concurrent_seconds:
        sample = ", ".join(f"{ts}×{cnt}" for ts, cnt in list(concurrent_seconds.items())[:3])
        patterns.append(f"PATTERN_CONCURRENT_RECONNECT — 同秒多次连接事件（{sample}）")
    if disconnect_count >= 5:
        patterns.append(f"PATTERN_FLAPPING       — 断线 {disconnect_count} 次（阈值 ≥5）")
    if outage_span_secs >= 300:
        patterns.append(f"PATTERN_EXTENDED_OUTAGE — 关键事件跨越 {outage_span_secs // 60} 分钟（阈值 ≥5 分钟）")
    if not patterns:
        patterns.append("PATTERN_CLEAN          — 无异常模式")

    # 历史案例引用（仅在 429 + 并发重连同时出现时）
    case_ref = ""
    if rate_limit_count >= 1 and concurrent_seconds:
        case_ref = (
            "\n[历史案例参考] PATTERN_429 + PATTERN_CONCURRENT_RECONNECT 组合，"
            "曾出现于 2026-04-16 BitMEX 新合约上线事件（XPTUSDT）（服务端主动踢连线 → 客户端并发重连 → REST 429）。"
            "本次是否相同根因，请结合关键事件行和 BitMEX status 页人工判断。"
        )

    concurrent_label = f"是（{len(concurrent_seconds)} 秒出现并发）" if concurrent_seconds else "否"
    summary = (
        f"\n=== 摘要 ===\n"
        f"窗口内日志：{total_lines} 行\n"
        f"断线/关闭：{disconnect_count} 次\n"
        f"连接/重连：{connect_count} 次\n"
        f"HTTP 429：{rate_limit_count} 次\n"
        f"并发重连：{concurrent_label}\n"
        f"\n[模式标签]\n" + "\n".join(f"  • {p}" for p in patterns)
        + case_ref
    )

    key_section = (
        f"\n\n=== 关键事件行（共 {len(key_lines)} 条，显示前 50）===\n"
        + ("\n".join(key_lines[:50]) if key_lines else "（无）")
        + (f"\n  ...还有 {len(key_lines) - 50} 条，用 verbose=True 查完整日志" if len(key_lines) > 50 else "")
    )

    status_link = (
        f"\n\n=== [外部确认] ===\n"
        f"如需核对 BitMEX 服务端事件，请访问：\n"
        f"  https://status.bitmex.com/\n"
        f"  时间窗口：{t_start_str} ~ {t_end_str} UTC\n"
        f"常见事件：新合约上线（每月 12:00 UTC）、API 限速调整、计划维护"
    )

    verbose_section = (
        f"\n\n=== 完整窗口日志（{total_lines} 行）===\n" + raw_logs
        if verbose else
        "\n\n如需完整日志，重跑时加 verbose=True"
    )

    return header + summary + key_section + status_link + verbose_section


if __name__ == "__main__":
    mcp.run()
