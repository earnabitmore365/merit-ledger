#!/usr/bin/env python3
"""
无极质检员 — 项目级质检 + 踩坑防线

用法：
    python3 wuji-verify.py <file_path>     # 单文件检查
    python3 wuji-verify.py --all           # 全项目扫描
"""

import ast
import hashlib
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime


# ==================== 项目根目录自动定位 ====================

def _find_project_root():
    """从当前文件位置向上找 .wuji-root 标记文件。"""
    p = os.path.dirname(os.path.abspath(__file__))
    # verify.py 在 ~/.claude/merit/ 下，不在项目内，用硬编码 fallback
    candidates = [
        os.path.expanduser("~/project/wuji-auto-trading"),
        "/Volumes/SSD-2TB/project/wuji-auto-trading",
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, ".wuji-root")):
            return c
    # 最后 fallback
    return "/Volumes/SSD-2TB/project/wuji-auto-trading"


_ROOT = _find_project_root()


# ==================== 踩坑防线：自动检查（pass/fail）====================

ANTI_PATTERNS = [
    # (描述, 正则模式, 严重度, 排除文件pattern)
    ("硬编码绝对路径 /Volumes/",
     r"/Volumes/SSD-2TB/",
     "❌", r"wuji-verify\.py|path_config\.py|CHANGELOG|\.md$"),
    ("entry<=0 旧写法（负数是合法mirror价格）",
     r"entry\s*<=\s*0",
     "❌", r"wuji-verify\.py"),
    ("硬编码 LEVERAGE（应从 constants.py import）",
     r"^\s*LEVERAGE\s*=\s*\d",
     "⚠️", r"constants\.py|team_config\.py"),
    ("硬编码 FEE_RATE（应从 constants.py import）",
     r"^\s*FEE_RATE\s*=\s*0\.\d",
     "⚠️", r"constants\.py|team_validation"),
    ("硬编码 SLIPPAGE_PCT（应从 constants.py import）",
     r"^\s*SLIPPAGE_PCT\s*=\s*0\.\d",
     "⚠️", r"constants\.py"),
    ("exec() 动态导入（用 importlib 代替）",
     r"exec\(f['\"]",
     "❌", None),
    ("mirror 旧保护 max(1e-8（不需要，负数合法）",
     r"max\(1e-8",
     "❌", r"wuji-verify\.py"),
    ("SMA/pivot 轴翻转（应直接取负）",
     r"sma.*as.*flip|pivot.*flip_?axis|mirror.*sma.*axis",
     "❌", r"wuji-verify\.py"),
    ("duckdb.connect 不带 read_only（只有 build_ 可以写）",
     r"duckdb\.connect\((?!.*read_only)[^)]+\)\s*$",
     "⚠️", r"build_klines|build_seed"),
    ("自定义 BARS_PER_DAY（应从 constants.py import）",
     r"^\s*_?BARS_PER_DAY\s*=\s*\{",
     "⚠️", r"constants\.py"),
    ("current_price<=0 旧写法（mirror负价格合法，应 ==0）",
     r"current_price\s*<=\s*0",
     "❌", r"wuji-verify\.py"),
    ("_highest_price<=0 旧写法（mirror负价格合法，应 ==0）",
     r"_highest_price\s*<=\s*0",
     "❌", r"wuji-verify\.py"),
    ("_lowest_price<=0 旧写法（mirror负价格合法，应 ==0）",
     r"_lowest_price\s*<=\s*0",
     "❌", r"wuji-verify\.py"),
    ("trailing stop 分母缺 abs（mirror负价格翻转符号）",
     r"/\s*self\._(?:highest|lowest)_price\s*$",
     "❌", r"wuji-verify\.py"),
    ("NULLIF(entry_price 缺 ABS（mirror负价格翻转PnL）",
     r"NULLIF\(entry_price",
     "❌", r"wuji-verify\.py"),
    ("close > 0 守卫（mirror负价格合法，应 close != 0）",
     r"close\s*>\s*0",
     "⚠️", r"wuji-verify\.py"),
]


# ==================== 回测-实盘一致性检查 ====================

CONSISTENCY_PAIRS = [
    # (文件A, 函数名A, 文件B, 函数名B)
    ("src/backtest/generate_seed.py", "_calc_pnl_pct",
     "trading/strategy_runner.py", "_calc_pnl_pct"),
    ("src/backtest/generate_seed.py", "_update_mfe_mae",
     "trading/strategy_runner.py", "_update_mfe_mae"),
    ("data/build_klines_indicators.py", "build_mirror_klines",
     "trading/strategy_runner.py", "_flip_klines"),
    ("src/core/risk/stop_loss.py", "_check_fixed_stop_loss",
     "src/backtest/generate_seed.py", "_check_stop_loss"),
]


def extract_func_body(filepath, func_name):
    """用 AST 提取函数体，返回 dump 字符串用于 hash 对比。"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                return ast.dump(node)
    except Exception:
        pass
    return None


def check_consistency():
    """检查回测-实盘函数对的一致性。"""
    results = []
    for file_a, func_a, file_b, func_b in CONSISTENCY_PAIRS:
        path_a = os.path.join(_ROOT, file_a)
        path_b = os.path.join(_ROOT, file_b)
        body_a = extract_func_body(path_a, func_a)
        body_b = extract_func_body(path_b, func_b)
        label = f"{func_a} ({os.path.basename(file_a)}) ↔ {func_b} ({os.path.basename(file_b)})"
        if body_a is None:
            results.append(f"  ⚠️ {file_a}:{func_a} 不存在（架构缺陷，非当次改动）")
        elif body_b is None:
            results.append(f"  ⚠️ {file_b}:{func_b} 不存在（架构缺陷，非当次改动）")
        elif func_a == func_b:
            # 同名函数：hash 应相等
            hash_a = hashlib.md5(body_a.encode()).hexdigest()
            hash_b = hashlib.md5(body_b.encode()).hexdigest()
            if hash_a == hash_b:
                results.append(f"  ✅ {label}: 回测=实盘")
            else:
                results.append(f"  ❌ {label}: 回测≠实盘")
        else:
            # 异名函数：hash 不一定相等，提醒人工确认
            results.append(f"  ⚠️ {label}: 异名函数，需人工确认逻辑一致")
    return results


# ==================== 踩坑提醒：不能自动查的（随机显示）====================

LESSONS = [
    "K线翻转就是加负号+HL对调。不要搞轴！不要SMA！不要max_price！",
    "做完了就是做完了。不要报告说做完但实际没做。",
    "回测改了实盘也要改。两边公式必须一样。",
    "py_compile 不算验证。要测逻辑不是测语法。",
    "同名文件不能有两份。改一份漏一份。",
    "先从3个策略测，对了再全量。不要一上来就跑10小时。",
    "不确定就说不确定。不要点头说对然后给偏了的方案。",
    "绕过基因库直接下单 = 违规。Alpha Arena教训：6个LLM 4个亏。",
    "Telegram Bot 必须有 chat_id 白名单。任何入口都要鉴权。",
    "SQLite 多线程写入必须加锁。不加 = 丢记录。",
    "止损后必须 ttp_manager.reset()。不重置 = 新仓继承旧TTP。",
    "Sortino 下行标准差以 0 为基准，不是 mean_ret。",
]


# ==================== 项目框架地图 ====================

REGISTRY = {
    "trading": {
        "name": "交易系统",
        "core_files": [
            f"{_ROOT}/trading/unified_trader.py",
            f"{_ROOT}/trading/strategy_runner.py",
            f"{_ROOT}/trading/kline_dispatcher.py",
            f"{_ROOT}/trading/limit_executor.py",
            f"{_ROOT}/trading/trade_logger.py",
            f"{_ROOT}/trading/trader_report.py",
            f"{_ROOT}/trading/trader_bot.py",
            f"{_ROOT}/trading/team_config.py",
            f"{_ROOT}/trading/monitor/monitor.py",
            f"{_ROOT}/trading/monitor/bitmex_dashboard.py",
        ],
        "cross_deps": [
            f"{_ROOT}/src/core/indicator_cache.py",
            f"{_ROOT}/src/core/constants.py",
            f"{_ROOT}/src/core/kline_utils.py",
            f"{_ROOT}/src/data/feed_gateway.py",
            f"{_ROOT}/src/data/feed_client.py",
            f"{_ROOT}/src/data/gateway_notifier.py",
            f"{_ROOT}/path_config.py",
        ],
        "docs": [
            f"{_ROOT}/README.md",
            f"{_ROOT}/ARCHITECTURE.md",
        ],
        "test_script": os.path.expanduser("~/.claude/merit/tests/test_trading_smoke.py"),
    },
    "backtest": {
        "name": "回测系统",
        "core_files": [
            f"{_ROOT}/src/backtest/generate_seed.py",
            f"{_ROOT}/src/backtest/backtest.py",
            f"{_ROOT}/backtest/build_seed_report.py",
            f"{_ROOT}/backtest/pipeline/refresh_summary.py",
        ],
        "cross_deps": [
            f"{_ROOT}/src/core/indicator_cache.py",
            f"{_ROOT}/src/core/constants.py",
            f"{_ROOT}/src/core/kline_utils.py",
            f"{_ROOT}/src/core/strategy/__init__.py",
            f"{_ROOT}/path_config.py",
        ],
        "docs": [
            f"{_ROOT}/README.md",
            f"{_ROOT}/ARCHITECTURE.md",
        ],
        "test_script": os.path.expanduser("~/.claude/merit/tests/test_backtest_smoke.py"),
    },
    "research": {
        "name": "研究/进化系统",
        "core_files": [
            f"{_ROOT}/src/core/indicator_cache.py",
            f"{_ROOT}/src/core/strategy/__init__.py",
        ],
        "cross_deps": [
            f"{_ROOT}/src/core/constants.py",
            f"{_ROOT}/path_config.py",
        ],
        "docs": [
            f"{_ROOT}/README.md",
            f"{_ROOT}/ARCHITECTURE.md",
        ],
        "test_script": os.path.expanduser("~/.claude/merit/tests/test_research_smoke.py"),
    },
}

# ==================== 代码-文档绑定 ====================

def _build_file_docs():
    """动态构建 FILE_DOCS：按目录规则批量绑定，不逐个硬编码。"""
    docs = {}

    # 目录 → 文档 映射规则
    DIR_DOC_MAP = {
        "src/exchange/bitmex": f"{_ROOT}/src/exchange/bitmex/README.md",
        "src/exchange/hyperliquid": f"{_ROOT}/src/exchange/hyperliquid/README.md",
        "src/exchange/paper": f"{_ROOT}/src/exchange/hyperliquid/README.md",
        "src/exchange": f"{_ROOT}/ARCHITECTURE.md",
        "src/exchange/binance": f"{_ROOT}/ARCHITECTURE.md",
        "src/data": f"{_ROOT}/data/README_KLINES_SEED.md",
        "src/backtest": f"{_ROOT}/backtest/README.md",
        "src/core/strategy": f"{_ROOT}/src/core/strategy/README.md",
        "src/core/risk": f"{_ROOT}/ARCHITECTURE.md",
        "src/core": f"{_ROOT}/ARCHITECTURE.md",
        "src/indicators": f"{_ROOT}/ARCHITECTURE.md",
        "src/trading": f"{_ROOT}/README.md",
        "src/ui": f"{_ROOT}/ARCHITECTURE.md",
        "trading/monitor": f"{_ROOT}/README.md",
        "trading/paper_trade": f"{_ROOT}/README.md",
        "trading": f"{_ROOT}/README.md",
        "backtest/gate": f"{_ROOT}/backtest/README.md",
        "backtest/pipeline": f"{_ROOT}/backtest/README.md",
        "backtest/regime": f"{_ROOT}/backtest/README.md",
        "backtest/dashboard": f"{_ROOT}/backtest/README.md",
        "backtest": f"{_ROOT}/backtest/README.md",
        "research/gp_engine": f"{_ROOT}/research/gp_engine/README.md",
        "research/sentinel_camp": f"{_ROOT}/ARCHITECTURE.md",
        "research/filters": f"{_ROOT}/ARCHITECTURE.md",
        "research/indicators": f"{_ROOT}/ARCHITECTURE.md",
        "research/selection": f"{_ROOT}/backtest/README.md",
        "research/simulation": f"{_ROOT}/backtest/README.md",
        "data": f"{_ROOT}/data/README_KLINES_SEED.md",
        "tests": f"{_ROOT}/ARCHITECTURE.md",
    }

    # 特殊绑定（覆盖目录规则）
    SPECIAL = {
        f"{_ROOT}/data/build_klines_indicators.py": f"{_ROOT}/data/README_KLINES_SEED.md",
        f"{_ROOT}/path_config.py": f"{_ROOT}/ARCHITECTURE.md",
    }
    docs.update(SPECIAL)

    # 扫描所有 .py 文件，按目录规则绑定
    for dirpath, dirs, files in os.walk(_ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", "autonomous")]
        for f in files:
            if not f.endswith(".py") or f.startswith("__"):
                continue
            full = os.path.join(dirpath, f)
            if full in docs:
                continue  # 已有特殊绑定
            rel_dir = os.path.relpath(dirpath, _ROOT)
            # 从最长前缀匹配
            matched_doc = None
            for prefix in sorted(DIR_DOC_MAP.keys(), key=len, reverse=True):
                if rel_dir == prefix or rel_dir.startswith(prefix + "/"):
                    matched_doc = DIR_DOC_MAP[prefix]
                    break
            if matched_doc:
                docs[full] = matched_doc

    return docs


FILE_DOCS = _build_file_docs()


# ==================== 检查函数 ====================

def find_frameworks(file_path):
    abs_path = os.path.abspath(file_path)
    matched = []
    for fw_id, fw in REGISTRY.items():
        all_files = fw.get("core_files", []) + fw.get("cross_deps", [])
        for f in all_files:
            if os.path.abspath(f) == abs_path:
                matched.append((fw_id, fw))
                break
    if not matched:
        for fw_id, fw in REGISTRY.items():
            for f in fw.get("core_files", []) + fw.get("cross_deps", []):
                f_dir = os.path.dirname(os.path.abspath(f))
                if abs_path.startswith(f_dir):
                    matched.append((fw_id, fw))
                    break
    return matched


def check_syntax(file_path):
    if not file_path.endswith(".py"):
        return "✅ 语法：非 .py 文件，跳过"
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile", file_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return "✅ 语法：py_compile 通过"
        return f"❌ 语法：{result.stderr.strip()[:150]}"
    except Exception as e:
        return f"❌ 语法：{e}"


def check_logic(frameworks):
    results = []
    for fw_id, fw in frameworks:
        test_script = fw.get("test_script")
        if not test_script:
            continue
        if not os.path.exists(test_script):
            results.append(f"⚠️ {os.path.basename(test_script)} 不存在")
            continue
        try:
            result = subprocess.run(
                ["python3", test_script],
                capture_output=True, text=True, timeout=60
            )
            name = os.path.basename(test_script)
            if result.returncode == 0:
                results.append(f"{name} ✅")
            else:
                results.append(f"{name} ❌ {result.stderr.strip()[:100]}")
        except Exception as e:
            results.append(f"❌ {e}")
    if not results:
        return "⏳ 逻辑：无自动测试"
    all_pass = all("✅" in r for r in results)
    return f"{'✅' if all_pass else '❌'} 逻辑：{'; '.join(results)}"


def check_chain(file_path, frameworks):
    abs_path = os.path.abspath(file_path)
    name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
    issues = []
    for fw_id, fw in frameworks:
        all_files = fw.get("core_files", []) + fw.get("cross_deps", [])
        for f in all_files:
            f_abs = os.path.abspath(f)
            if f_abs == abs_path or not os.path.exists(f_abs):
                continue
            try:
                result = subprocess.run(
                    ["grep", "-l", name_no_ext, f_abs],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    issues.append(os.path.basename(f_abs))
            except Exception:
                pass
    if not issues:
        return "✅ 全链路：grep 未发现引用"
    unique = list(dict.fromkeys(issues))
    return f"⏳ 全链路：被 {', '.join(unique)} 引用，需确认改动兼容"


def check_docs(file_path, frameworks):
    basename = os.path.basename(file_path)
    issues = []
    for fw_id, fw in frameworks:
        for doc in fw.get("docs", []):
            if not os.path.exists(doc):
                continue
            try:
                with open(doc, encoding="utf-8") as f:
                    content = f.read()
                if basename in content:
                    issues.append(f"{os.path.basename(doc)} 引用了 {basename}")
            except Exception:
                pass
    if not issues:
        return "✅ 文档：无需更新"
    return f"⏳ 文档：{'; '.join(issues)}，确认内容同步"


def check_doc_freshness(file_path):
    abs_path = os.path.abspath(file_path)
    doc_path = FILE_DOCS.get(abs_path)
    if not doc_path or not os.path.exists(doc_path):
        return None
    code_mtime = os.path.getmtime(abs_path)
    doc_mtime = os.path.getmtime(doc_path)
    doc_name = os.path.basename(doc_path)
    if code_mtime > doc_mtime:
        gap_hours = int((code_mtime - doc_mtime) / 3600)
        return f"⚠️ 文档可能过时：{doc_name}（代码比文档新 {gap_hours}h）"
    return f"✅ 文档同步：{doc_name}"


def check_anti_patterns(file_path):
    """检查单个文件的反模式。返回 (pass_count, fail_count, warnings)。"""
    if not file_path.endswith(".py"):
        return 0, 0, []

    basename = os.path.basename(file_path)
    warnings = []
    pass_count = 0
    fail_count = 0

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return 0, 0, []

    for desc, pattern, severity, exclude in ANTI_PATTERNS:
        if exclude and re.search(exclude, basename):
            continue
        hits = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                hits.append(i)
        if hits:
            line_str = ",".join(str(h) for h in hits[:5])
            if len(hits) > 5:
                line_str += f"...+{len(hits)-5}"
            warnings.append(f"  {severity} {desc}：行 {line_str}")
            fail_count += 1
        else:
            pass_count += 1

    return pass_count, fail_count, warnings


def check_duplicate_files():
    """检查项目中同名 .py 文件出现在多个目录。"""
    file_map = {}  # basename -> [full_paths]
    for dirpath, dirs, files in os.walk(_ROOT):
        # 跳过 __pycache__ 和 .git
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for f in files:
            if f.endswith(".py"):
                full = os.path.join(dirpath, f)
                if os.path.islink(full):
                    continue  # 跳过软链接
                file_map.setdefault(f, []).append(full)

    dupes = []
    for name, paths in sorted(file_map.items()):
        if len(paths) > 1:
            rel_paths = [os.path.relpath(p, _ROOT) for p in paths]
            dupes.append(f"  ❌ {name} 出现在 {len(paths)} 处：{', '.join(rel_paths)}")
    return dupes


def check_unregistered_files():
    """找出没有在 FILE_DOCS 注册的 .py 文件。"""
    registered = set(FILE_DOCS.keys())
    unregistered = []

    for dirpath, dirs, files in os.walk(_ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules", "autonomous")]
        for f in files:
            if f.endswith(".py") and not f.startswith("__"):
                full = os.path.join(dirpath, f)
                if full not in registered:
                    rel = os.path.relpath(full, _ROOT)
                    unregistered.append(rel)

    return unregistered


def check_todo_fixme():
    """扫描项目中的 TODO/FIXME/HACK/XXX 注释。"""
    try:
        result = subprocess.run(
            ["grep", "-rn", r"TODO\|FIXME\|HACK\|XXX", "--include=*.py", _ROOT],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        count = len(lines)
        output = [f"  📌 TODO/FIXME/HACK/XXX: {count} 条"]
        for line in lines[:10]:
            # 缩短路径显示
            rel = line.replace(_ROOT + "/", "", 1)
            output.append(f"    {rel}")
        if count > 10:
            output.append(f"    ...还有 {count - 10} 条")
        return output
    except Exception as e:
        return [f"  ❌ TODO 扫描失败：{e}"]


def check_paths():
    """验证 path_config 中定义的路径是否存在。"""
    results = []
    sys.path.insert(0, _ROOT)
    try:
        # 强制重新加载以获取最新路径
        if "path_config" in sys.modules:
            del sys.modules["path_config"]
        import path_config as pc
        paths = {}
        for attr in dir(pc):
            val = getattr(pc, attr)
            if isinstance(val, str) and os.path.sep in val and attr.isupper():
                paths[attr] = val
        for name in sorted(paths):
            path = paths[name]
            status = "✅" if os.path.exists(path) else "❌"
            results.append(f"  {status} {name}: {path}")
    except ImportError as e:
        results.append(f"  ❌ path_config 导入失败：{e}")
    except Exception as e:
        results.append(f"  ❌ path_config 检查失败：{e}")
    finally:
        sys.path.pop(0)
    return results


# ==================== 输出 ====================

def show_lessons():
    """随机显示3条踩坑提醒。"""
    picks = random.sample(LESSONS, min(3, len(LESSONS)))
    print("\n💀 踩坑提醒（每条都是血的教训）：")
    for p in picks:
        print(f"  💀 {p}")
    print()


def verify_single(file_path):
    """单文件检查。"""
    abs_path = os.path.abspath(file_path)
    basename = os.path.basename(file_path)

    if not os.path.exists(abs_path):
        print(f"❌ 文件不存在: {abs_path}")
        return

    frameworks = find_frameworks(abs_path)

    print(f"═══ 无极质检: {basename} ═══")
    if frameworks:
        print(f"框架：{', '.join(fw['name'] for _, fw in frameworks)}")
    else:
        print("框架：未注册（只做语法+反模式检查）")

    # 四件套
    r_syntax = check_syntax(abs_path)
    r_logic = check_logic(frameworks)
    r_chain = check_chain(abs_path, frameworks)
    r_docs = check_docs(abs_path, frameworks)
    r_freshness = check_doc_freshness(abs_path)

    print(r_syntax)
    print(r_logic)
    print(r_chain)
    print(r_docs)
    if r_freshness:
        print(r_freshness)

    # 反模式检查
    p, f, warns = check_anti_patterns(abs_path)
    if warns:
        print(f"\n🔍 反模式检查（{p} pass, {f} fail）：")
        for w in warns:
            print(w)
    elif abs_path.endswith(".py"):
        print(f"✅ 反模式：{p} 项全部通过")

    # 写结果
    _write_result(basename, r_syntax, r_logic, r_chain, r_docs, f)


def verify_all():
    """全项目扫描。"""
    print("═══ 无极质检：全项目扫描 ═══")
    print(f"项目根：{_ROOT}\n")

    show_lessons()

    # 1. 同名文件检测
    print("── 同名文件检测 ──")
    dupes = check_duplicate_files()
    if dupes:
        for d in dupes:
            print(d)
    else:
        print("  ✅ 无同名文件")

    # 2. 未注册文件检测
    print("\n── 未注册文件（不在 FILE_DOCS 中）──")
    unreg = check_unregistered_files()
    if unreg:
        print(f"  ⚠️ {len(unreg)} 个 .py 文件未注册：")
        for u in unreg[:20]:
            print(f"    {u}")
        if len(unreg) > 20:
            print(f"    ...还有 {len(unreg)-20} 个")
    else:
        print("  ✅ 所有文件已注册")

    # 3. 全项目反模式扫描
    print("\n── 反模式扫描 ──")
    total_pass = 0
    total_fail = 0
    file_count = 0
    all_warns = []

    for dirpath, dirs, files in os.walk(_ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for f in files:
            if f.endswith(".py"):
                full = os.path.join(dirpath, f)
                file_count += 1
                p, fail, warns = check_anti_patterns(full)
                total_pass += p
                total_fail += fail
                if warns:
                    rel = os.path.relpath(full, _ROOT)
                    all_warns.append((rel, warns))

    if all_warns:
        for rel, warns in all_warns:
            print(f"\n  📄 {rel}：")
            for w in warns:
                print(f"  {w}")
        print(f"\n  总计：{total_pass} pass, {total_fail} fail")
    else:
        print(f"  ✅ 全部通过（{total_pass} 项检查）")

    # 4. 文档新鲜度检查
    print("\n── 文档新鲜度 ──")
    stale = []
    for code_path, doc_path in FILE_DOCS.items():
        if not os.path.exists(code_path) or not os.path.exists(doc_path):
            continue
        if os.path.getmtime(code_path) > os.path.getmtime(doc_path):
            gap_h = int((os.path.getmtime(code_path) - os.path.getmtime(doc_path)) / 3600)
            stale.append(f"  ⚠️ {os.path.relpath(code_path, _ROOT)} → {os.path.basename(doc_path)}（{gap_h}h）")
    if stale:
        for s in stale:
            print(s)
    else:
        print("  ✅ 所有文档同步")

    # 5. path_config 路径验证
    print("\n── path_config 路径验证 ──")
    path_results = check_paths()
    for r in path_results:
        print(r)

    # 6. 回测-实盘一致性检查
    print("\n── 回测-实盘一致性 ──")
    consistency_results = check_consistency()
    for r in consistency_results:
        print(r)

    # 7. TODO/FIXME 扫描
    print("\n── TODO/FIXME ──")
    todo_results = check_todo_fixme()
    for r in todo_results:
        print(r)

    # 扫描统计硬数字
    py_count = file_count
    print(f"\n📊 扫描统计：")
    print(f"  .py 文件总数：{py_count}")
    print(f"  实际扫描：{py_count}/{py_count}")
    print(f"  命中反模式：{total_fail}")
    # 写 scan_stats.json 供队长验收读取
    try:
        stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_stats.json")
        with open(stats_path, "w") as sf:
            json.dump({"time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "total_py_files": py_count, "scanned": py_count,
                        "hits": total_fail}, sf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    print(f"\n═══ 扫描完成 ═══")


def _write_result(basename, r_syntax, r_logic, r_chain, r_docs, anti_fails):
    def _status(line):
        if line.startswith("✅"):
            return "pass"
        if line.startswith("❌"):
            return "fail"
        return "pending"

    result_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_result.json")
    try:
        result = {
            "file": basename,
            "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "results": {
                "syntax": _status(r_syntax),
                "logic": _status(r_logic),
                "chain": _status(r_chain),
                "docs": _status(r_docs),
                "anti_patterns": "fail" if anti_fails > 0 else "pass",
            },
            "pass_count": sum(1 for r in [r_syntax, r_logic, r_chain, r_docs] if r.startswith("✅")) + (1 if anti_fails == 0 else 0),
            "total": 5,
        }
        with open(result_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def verify_pre(files):
    """开工前检查：轻量快速，提醒规则和雷区。"""
    print("═══ 无极质检：开工前 (--pre) ═══\n")

    show_lessons()

    # 全项目反模式状态
    total_fail = 0
    for dirpath, dirs, fnames in os.walk(_ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for fn in fnames:
            if fn.endswith(".py"):
                _, fail, _ = check_anti_patterns(os.path.join(dirpath, fn))
                total_fail += fail

    if total_fail > 0:
        print(f"⚠️ 项目当前有 {total_fail} 个反模式违规（先修再干活）")
    else:
        print("✅ 项目反模式：全部通过")

    # 目标文件的文档绑定
    if files:
        print(f"\n── 本次涉及文件 ──")
        for fp in files:
            abs_fp = os.path.abspath(fp)
            basename = os.path.basename(fp)
            doc = FILE_DOCS.get(abs_fp)
            if doc:
                doc_name = os.path.basename(doc)
                exists = "✅" if os.path.exists(doc) else "❌ 不存在"
                print(f"  {basename} → {doc_name} {exists}")
            else:
                print(f"  {basename} → 未绑定文档")

    # 保存 pre 状态（供 --post 对比）
    pre_state = {"time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), "total_fail": total_fail}
    pre_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_pre_state.json")
    try:
        with open(pre_path, "w") as f:
            json.dump(pre_state, f)
    except Exception:
        pass

    print(f"\n═══ 开工吧 ═══")


def verify_post(files):
    """交活前检查：全面验证，不能比开工前更差。"""
    print("═══ 无极质检：交活前 (--post) ═══\n")

    # 读 pre 状态
    pre_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_pre_state.json")
    pre_fail = None
    try:
        with open(pre_path) as f:
            pre_state = json.load(f)
            pre_fail = pre_state.get("total_fail", 0)
            print(f"对比基准：--pre 时 {pre_fail} 个违规")
    except Exception:
        print("⚠️ 未找到 --pre 状态，跳过对比")

    # 逐文件全量检查
    all_clean = True
    for fp in files:
        abs_fp = os.path.abspath(fp)
        if not os.path.exists(abs_fp):
            print(f"❌ 文件不存在: {fp}")
            all_clean = False
            continue

        basename = os.path.basename(fp)
        frameworks = find_frameworks(abs_fp)
        print(f"\n── {basename} ──")

        # 语法
        r = check_syntax(abs_fp)
        print(f"  {r}")
        if r.startswith("❌"):
            all_clean = False

        # 反模式
        p, fail, warns = check_anti_patterns(abs_fp)
        if warns:
            print(f"  🔍 反模式（{fail} fail）：")
            for w in warns:
                print(f"  {w}")
            all_clean = False
        else:
            print(f"  ✅ 反模式：{p} 项通过")

        # 文档新鲜度
        r_fresh = check_doc_freshness(abs_fp)
        if r_fresh:
            print(f"  {r_fresh}")

    # 全项目 fail 对比
    total_fail = 0
    post_file_count = 0
    for dirpath, dirs, fnames in os.walk(_ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for fn in fnames:
            if fn.endswith(".py"):
                post_file_count += 1
                _, fail, _ = check_anti_patterns(os.path.join(dirpath, fn))
                total_fail += fail

    print(f"\n── 全项目反模式 ──")
    if pre_fail is not None:
        diff = total_fail - pre_fail
        if diff > 0:
            print(f"  ❌ 新增 {diff} 个违规！（{pre_fail} → {total_fail}）")
            all_clean = False
        elif diff < 0:
            print(f"  ✅ 减少 {abs(diff)} 个违规（{pre_fail} → {total_fail}）")
        else:
            print(f"  ✅ 无新增违规（{total_fail}）")
    else:
        print(f"  当前 {total_fail} 个违规")

    # 回测-实盘一致性检查
    print(f"\n── 回测-实盘一致性 ──")
    consistency_results = check_consistency()
    for r in consistency_results:
        print(r)
    if any("❌" in r for r in consistency_results):
        all_clean = False

    # TODO/FIXME 扫描
    print(f"\n── TODO/FIXME ──")
    todo_results = check_todo_fixme()
    for r in todo_results:
        print(r)

    # 扫描统计硬数字
    print(f"\n📊 扫描统计：")
    print(f"  .py 文件总数：{post_file_count}")
    print(f"  实际扫描：{post_file_count}/{post_file_count}")
    print(f"  命中反模式：{total_fail}")
    try:
        stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_stats.json")
        with open(stats_path, "w") as sf:
            json.dump({"time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "total_py_files": post_file_count, "scanned": post_file_count,
                        "hits": total_fail}, sf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if all_clean:
        print(f"\n✅ 可以交活")
    else:
        print(f"\n❌ 有问题，修完再交")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 wuji-verify.py <file_path>        # 单文件检查")
        print("  python3 wuji-verify.py --all               # 全项目扫描")
        print("  python3 wuji-verify.py --pre [files...]    # 开工前检查")
        print("  python3 wuji-verify.py --post <files...>   # 交活前检查")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "--all":
        verify_all()
    elif cmd == "--pre":
        verify_pre(sys.argv[2:])
    elif cmd == "--post":
        verify_post(sys.argv[2:])
    else:
        show_lessons()
        verify_single(cmd)


if __name__ == "__main__":
    main()
