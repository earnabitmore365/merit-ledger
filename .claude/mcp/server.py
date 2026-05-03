#!/usr/bin/env python3
"""
Pine MCP Server — Pine Script v6 生成工具集

分步状态锁（check_code 确认码链，技术强制不跳步）:
  1. pine_read_docs     → 输出 _check_code
  2. pine_render        → 需传入上一步的 check_code → 输出新的 _check_code
  3. pine_validate      → 需传入上一步的 check_code → 输出新的 _check_code
  4. pine_write         → 需传入上一步的 check_code → 完成

不调前一步 → 拿不到 check_code → 无法调下一步。
"""

import os
import re
import secrets
import textwrap
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Pine Script Generator")

DOWNLOADS_DIR = os.path.expanduser("~/Downloads")
WIKI_ROOT = "/Volumes/SSD-2TB/无极开天"
TEMPLATES_DIR = "知识库/两仪/自动交易系统/回测/策略"
KB_PATH = os.path.join(WIKI_ROOT, TEMPLATES_DIR)

# ── 分步状态锁 ──────────────────────────────────────────────────────────
_state = "idle"  # idle → docs_read → rendered → validated → done
_next_code: str | None = None


def _gen_code(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def _check(step_name: str, expected_state: str, check_code: str | None):
    """通用状态+确认码检查"""
    global _state, _next_code
    if _state != expected_state:
        expected_calls = {
            "docs_read": "pine_read_docs",
            "rendered": "pine_render",
            "validated": "pine_validate",
        }
        needed = expected_calls.get(expected_state, expected_state)
        return {"error": f"⛔ 顺序错误：当前状态是「{_state}」，调 {step_name} 前必须先调 {needed}"}
    if not check_code or check_code != _next_code:
        return {"error": f"⛔ check_code 不匹配：必须传入上一步返回的 _check_code 才能调 {step_name}"}
    return None


def _transit(new_state: str, prefix: str):
    """前进到下一状态，生成新确认码"""
    global _state, _next_code
    _state = new_state
    _next_code = _gen_code(prefix)


# ══════════════════════════════════════════════════════════════════════════
# 模板 — 信号 indicator（4 种）
# ══════════════════════════════════════════════════════════════════════════

INDICATOR_TEMPLATES: dict[str, str] = {
    "supertrend": textwrap.dedent("""\
    //@version=6
    indicator("{name} Signal", overlay=true)
    atrPeriod  = input.int({atr_period}, "ATR Period", minval=1, maxval=100)
    multiplier = input.float({multiplier}, "Multiplier", minval=0.5, maxval=20.0, step=0.5)
    [stLine, stDir] = ta.supertrend(multiplier, atrPeriod)
    longCond  = stDir == -1 and stDir[1] == 1
    shortCond = stDir == 1  and stDir[1] == -1
    plot(longCond ? 1.0 : shortCond ? -1.0 : 0.0, "Signal", display=display.none)
    plot(stLine, "SuperTrend", color=stDir == -1 ? color.green : color.red, linewidth=2)
    plotshape(longCond,  "Buy",  shape.triangleup,   location.belowbar, color.green, size=size.small)
    plotshape(shortCond, "Sell", shape.triangledown, location.abovebar, color.red,   size=size.small)
    """),
    "macd": textwrap.dedent("""\
    //@version=6
    indicator("{name} Signal", overlay=false)
    fastPeriod   = input.int({fast_period}, "Fast Period",   minval=2, maxval=50)
    slowPeriod   = input.int({slow_period}, "Slow Period",   minval=3, maxval=200)
    signalPeriod = input.int({signal_period}, "Signal Period", minval=2, maxval=50)
    [macdLine, signalLine, histLine] = ta.macd(close, fastPeriod, slowPeriod, signalPeriod)
    longCond  = histLine > 0 and histLine[1] <= 0
    shortCond = histLine < 0 and histLine[1] >= 0
    plot(longCond ? 1.0 : shortCond ? -1.0 : 0.0, "Signal", display=display.none)
    plot(macdLine,   "MACD",      color=color.blue)
    plot(signalLine, "Signal Line", color=color.orange)
    histColor = histLine >= 0 ? color.new(color.green, 30) : color.new(color.red, 30)
    plot(histLine, "Histogram", style=plot.style_histogram, color=histColor)
    hline(0, "Zero", color=color.gray, linestyle=hline.style_dashed)
    """),
    "rsi": textwrap.dedent("""\
    //@version=6
    indicator("{name} Signal", overlay=false)
    rsiPeriod  = input.int({rsi_period}, "RSI Period",    minval=2, maxval=100)
    oversold   = input.int({oversold}, "Oversold",      minval=5, maxval=50)
    overbought = input.int({overbought}, "Overbought",    minval=50, maxval=95)
    rsi = ta.rsi(close, rsiPeriod)
    longCond  = ta.crossover(rsi, oversold)
    shortCond = ta.crossunder(rsi, overbought)
    plot(longCond ? 1.0 : shortCond ? -1.0 : 0.0, "Signal", display=display.none)
    plot(rsi, "RSI", color=color.purple)
    hline(overbought, "Overbought", color=color.red,   linestyle=hline.style_dashed)
    hline(oversold,   "Oversold",   color=color.green, linestyle=hline.style_dashed)
    hline(50, "Mid", color=color.gray, linestyle=hline.style_dotted)
    """),
    "ema_cross": textwrap.dedent("""\
    //@version=6
    indicator("{name} Signal", overlay=true)
    fastLen = input.int({fast_len}, "Fast EMA", minval=1, maxval=200)
    slowLen = input.int({slow_len}, "Slow EMA", minval=2, maxval=500)
    emaFast = ta.ema(close, fastLen)
    emaSlow = ta.ema(close, slowLen)
    longCond  = ta.crossover(emaFast, emaSlow)
    shortCond = ta.crossunder(emaFast, emaSlow)
    plot(longCond ? 1.0 : shortCond ? -1.0 : 0.0, "Signal", display=display.none)
    plot(emaFast, "EMA Fast", color=color.blue)
    plot(emaSlow, "EMA Slow", color=color.orange)
    """),
}


def _render_indicator(name: str, indicator_type: str, params: dict[str, Any]) -> str:
    template = INDICATOR_TEMPLATES.get(indicator_type)
    if not template:
        raise ValueError(f"不支持的指标类型: {indicator_type}")
    fmt_params = {"name": name}
    if indicator_type == "supertrend":
        fmt_params["atr_period"] = params.get("atr_period", 10)
        fmt_params["multiplier"] = params.get("multiplier", 3.0)
    elif indicator_type == "macd":
        fmt_params["fast_period"] = params.get("fast_period", 12)
        fmt_params["slow_period"] = params.get("slow_period", 26)
        fmt_params["signal_period"] = params.get("signal_period", 9)
    elif indicator_type == "rsi":
        fmt_params["rsi_period"] = int(params.get("rsi_period", 14))
        fmt_params["oversold"] = int(params.get("oversold", 30))
        fmt_params["overbought"] = int(params.get("overbought", 70))
    elif indicator_type == "ema_cross":
        fmt_params["fast_len"] = params.get("fast_len", 9)
        fmt_params["slow_len"] = params.get("slow_len", 21)
    return template.format(**fmt_params)


def _check_kb_entry(indicator_type: str) -> str | None:
    """检查模板对应的知识库条目是否存在。"""
    slug = indicator_type.replace("_", "-")
    expected = os.path.join(KB_PATH, f"pine-{slug}-signal.md")
    if not os.path.exists(expected):
        known = ", ".join(sorted(INDICATOR_TEMPLATES.keys()))
        return (
            f"⛔ 知识库条目缺失：{TEMPLATES_DIR}/pine-{slug}-signal.md 不存在\n"
            f"   加新模板必须先用 /wiki 写对应的知识库条目。\n"
            f"   已有模板类型：{known}"
        )
    return None


# ══════════════════════════════════════════════════════════════════════════
# 模板 — 开单 strategy（3 种）
# ══════════════════════════════════════════════════════════════════════════

def _render_strategy(strategy_type: Literal["pure", "ttp_close", "ttp_highlow"]) -> str:
    strategies = {
        "pure": textwrap.dedent("""\
        //@version=6
        strategy("Pure Signal Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10, margin_long=0, margin_short=0)
        sig = input.source(close, "Signal Source")
        longEntry  = sig == 1.0
        shortEntry = sig == -1.0
        longExit   = sig == -1.0
        shortExit  = sig == 1.0
        if longEntry
            strategy.entry("Long", strategy.long)
        if shortEntry
            strategy.entry("Short", strategy.short)
        if longExit and strategy.position_size > 0
            strategy.close("Long")
        if shortExit and strategy.position_size < 0
            strategy.close("Short")
        plot(sig, "Signal", color=color.gray, linewidth=1, style=plot.style_line)
        """),
        "ttp_close": textwrap.dedent("""\
        //@version=6
        strategy("TTP Close Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10, margin_long=0, margin_short=0)
        trailPct   = input.float(5.0, "Trail %", minval=0.1, maxval=50.0, step=0.5)
        sig        = input.source(close, "Signal Source")
        longEntry  = sig == 1.0
        shortEntry = sig == -1.0
        longExit   = sig == -1.0 and strategy.position_size > 0
        shortExit  = sig == 1.0 and strategy.position_size < 0
        if longEntry and strategy.position_size <= 0
            strategy.entry("Long", strategy.long)
        if shortEntry and strategy.position_size >= 0
            strategy.entry("Short", strategy.short)
        if strategy.position_size > 0
            strategy.exit("TTP Long", "Long", trail_price=close, trail_offset=close * (trailPct / 100))
        if strategy.position_size < 0
            strategy.exit("TTP Short", "Short", trail_price=close, trail_offset=close * (trailPct / 100))
        if longExit
            strategy.close("Long")
        if shortExit
            strategy.close("Short")
        plot(sig, "Signal", color=color.gray, linewidth=1, style=plot.style_line)
        """),
        "ttp_highlow": textwrap.dedent("""\
        //@version=6
        strategy("TTP HighLow Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10, margin_long=0, margin_short=0)
        trailPct   = input.float(5.0, "Trail %", minval=0.1, maxval=50.0, step=0.5)
        sig        = input.source(close, "Signal Source")
        longEntry  = sig == 1.0
        shortEntry = sig == -1.0
        longExit   = sig == -1.0 and strategy.position_size > 0
        shortExit  = sig == 1.0 and strategy.position_size < 0
        if longEntry and strategy.position_size <= 0
            strategy.entry("Long", strategy.long)
        if shortEntry and strategy.position_size >= 0
            strategy.entry("Short", strategy.short)
        if strategy.position_size > 0
            strategy.exit("TTP Long", "Long", trail_price=high, trail_offset=high * (trailPct / 100))
        if strategy.position_size < 0
            strategy.exit("TTP Short", "Short", trail_price=low, trail_offset=low * (trailPct / 100))
        if longExit
            strategy.close("Long")
        if shortExit
            strategy.close("Short")
        plot(sig, "Signal", color=color.gray, linewidth=1, style=plot.style_line)
        """),
    }
    t = strategies.get(strategy_type)
    if not t:
        raise ValueError(f"不支持的策略类型: {strategy_type}")
    return t


# ══════════════════════════════════════════════════════════════════════════
# 验证 + 写入
# ══════════════════════════════════════════════════════════════════════════

def _validate_code(code: str) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if "//@version=6" not in code:
        issues.append({"rule": "缺少 //@version=6", "severity": "error"})
    if "```" in code:
        issues.append({"rule": "包含 markdown 代码围栏", "severity": "error"})
    if "indicator(" not in code and "strategy(" not in code:
        issues.append({"rule": "indicator() 或 strategy() 缺失", "severity": "error"})
    if "strategy(" in code:
        matches = re.findall(r"strategy\([^)]*\)", code)
        if not matches or any("\n" in m for m in matches):
            issues.append({"rule": "strategy() 包含换行符，必须写单行", "severity": "error"})
    if "indicator(" in code and "strategy(" not in code and "plot(" not in code:
        issues.append({"rule": "indicator 没有 plot 输出", "severity": "error"})
    if "when=" in code:
        issues.append({"rule": "使用了已废弃的 when= 参数", "severity": "error"})
    return {"pass": all(i["severity"] != "error" for i in issues), "issues": issues}


def _write_pine(code: str, filename: str) -> dict[str, Any]:
    if not filename.endswith(".md"):
        filename += ".md"
    filepath = os.path.join(DOWNLOADS_DIR, filename)
    clean = re.sub(r"^```(pine)?\n?|```$", "", code) if "```" in code else code
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(clean.strip() + "\n")
    return {"path": filepath, "size": len(clean)}


# ══════════════════════════════════════════════════════════════════════════
# MCP 工具（分步状态锁，check_code 强制串行）
# ══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def pine_read_docs() -> dict:
    """Step 1 — 搜知识库找 Pine Script 文档，返回规则摘要。

    必须先调此工具，拿到 _check_code 才能调后续工具。
    """
    global _state, _next_code
    if _state != "idle" and _state != "done":
        return {"error": f"⛔ 本轮流程已开始（当前状态：{_state}），pine_read_docs 只能在一轮开始时调"}

    keywords = ["pine", "pine-script", "pinescript", "pine script"]
    hits = []

    for dirpath, _dirs, files in os.walk(WIKI_ROOT):
        for f in files:
            if not f.endswith(".md"):
                continue
            fpath = os.path.join(dirpath, f)
            rel = os.path.relpath(fpath, WIKI_ROOT)
            fname_lower = f.lower()
            if any(kw in fname_lower for kw in keywords):
                hits.append((rel, 0, "文件名匹配"))
            try:
                with open(fpath, encoding="utf-8") as fh:
                    content = fh.read(10000)
            except Exception:
                continue
            tag_match = re.search(r"tags:\s*\n((?:\s+-\s+\S+\s*\n)*)", content)
            if tag_match:
                tag_block = tag_match.group(1).lower()
                if any(kw in tag_block for kw in keywords):
                    hits.append((rel, 2, "标签匹配"))
                    continue
            lines = content.lower().splitlines()
            for i, line in enumerate(lines):
                if any(kw in line for kw in keywords):
                    hits.append((rel, i + 1, f"内容匹配 — L{i+1}"))
                    break

    skip_prefixes = ("raw/", "知识库/README.md")
    seen = set()
    unique_hits = []
    for rel, line, reason in hits:
        if rel.startswith(skip_prefixes):
            continue
        if rel not in seen:
            seen.add(rel)
            unique_hits.append((rel, line, reason))

    def sort_key(item):
        rel = item[0]
        if rel.startswith("知识库/规则/"):
            return 0
        if rel.startswith("技术/"):
            return 1
        if rel.startswith("踩坑/"):
            return 2
        if rel.startswith("知识库/"):
            return 3
        return 9
    unique_hits.sort(key=sort_key)

    docs = []
    for rel, _line, _reason in unique_hits[:6]:
        fpath = os.path.join(WIKI_ROOT, rel)
        try:
            with open(fpath, encoding="utf-8") as fh:
                raw = fh.read()
        except Exception:
            continue
        title_match = re.search(r"^#\s+(.+)", raw, re.MULTILINE)
        title = title_match.group(1) if title_match else rel
        tag_match = re.search(r"tags:\s*\n((?:\s+-\s+\S+\s*\n)*)", raw)
        tags_list = re.findall(r"- (\S+)", tag_match.group(1)) if tag_match else []
        conf_match = re.search(r"confidence:\s*(\S+)", raw)
        confidence = conf_match.group(1) if conf_match else "unknown"
        rules = []
        conclusion_match = re.search(r"## 结论\s*\n(.+?)(?=\n##|\Z)", raw, re.DOTALL)
        if conclusion_match:
            rules_raw = conclusion_match.group(1).strip()
            rules = [l.strip("- ").strip() for l in rules_raw.splitlines() if l.strip() and not l.strip().startswith("---")][:8]
        else:
            raw_lines = raw.splitlines()
            for line in raw_lines[3:60]:
                stripped = line.strip()
                if stripped and not stripped.startswith("---") and not stripped.startswith("tags:") and not stripped.startswith("id:"):
                    rules.append(stripped[:150])
                    if len(rules) >= 8:
                        break
        docs.append({
            "path": rel,
            "title": title,
            "tags": tags_list[:6],
            "confidence": confidence,
            "rules": rules,
        })

    _transit("docs_read", "rd")
    result = {
        "matched_files": len(unique_hits),
        "files_read": len(docs),
        "documents": docs,
        "_check_code": _next_code,
        "_next_step": "pine_render 或直接将代码传给 pine_validate",
        "confirmation_required": (
            "\n━━━━ 强制确认（不完成不可继续）━━━━\n\n"
            "现在逐条输出以下确认，每条必须具体到\"这条规则对应当前策略的哪个部分\"：\n\n"
            "规则 1：「……」（文档 X）\n  → 对应当前策略：______\n\n"
            "规则 2：「……」（文档 Y）\n  → 对应当前策略：______\n\n"
            "……\n\n"
            "要求：\n"
            "1. 每一条规则都要填\"对应当前策略\"的具体位置\n"
            "2. 文档没讲清楚 / 确认不了的规则 → 上网搜 → 存 wiki → 回来\n"
            "3. 上网也查不到 → 停下问老祖\n"
            "4. 全部确认完 → 调 pine_render（走模板）或 pine_validate（手写代码）\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
    }
    return result


@mcp.tool()
def pine_render(
    check_code: str,
    output_type: str,
    strategy_name: str | None = None,
    indicator_type: str | None = None,
    strategy_type: str | None = None,
    params: dict | None = None,
) -> dict:
    """Step 2 — 生成 Pine Script v6 代码。

    必须先调 pine_read_docs 拿到 _check_code 传入。
    check_code: 上一步返回的 _check_code
    output_type: "indicator"（信号指标）或 "strategy"（开单策略）
    indicator_type: "supertrend"/"macd"/"rsi"/"ema_cross"
    strategy_type: "pure"/"ttp_close"/"ttp_highlow"
    params: 参数 dict，如 {"rsi_period": 5, "oversold": 15, "overbought": 85}
    """
    err = _check("pine_render", "docs_read", check_code)
    if err:
        return err

    try:
        if output_type == "indicator":
            if not indicator_type:
                return {"error": "indicator 模式需要指定 indicator_type"}
            kb_err = _check_kb_entry(indicator_type)
            if kb_err:
                return {"error": kb_err}
            code = _render_indicator(
                name=strategy_name or "Strategy",
                indicator_type=indicator_type,
                params=params or {},
            )
            _transit("rendered", "re")
            return {
                "code": code,
                "code_type": f"indicator/{indicator_type}",
                "_check_code": _next_code,
                "_next_step": "pine_validate",
            }
        elif output_type == "strategy":
            if not strategy_type:
                return {"error": "strategy 模式需要指定 strategy_type"}
            code = _render_strategy(strategy_type)
            _transit("rendered", "re")
            return {
                "code": code,
                "code_type": f"strategy/{strategy_type}",
                "_check_code": _next_code,
                "_next_step": "pine_validate",
            }
        else:
            return {"error": f"不支持的 output_type: {output_type}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def pine_validate(check_code: str, code: str) -> dict:
    """Step 3 — 验证 Pine Script v6 代码格式。

    必须先调 pine_render 拿到 _check_code 传入。
    手写代码时可在 pine_read_docs 后直接调此工具。
    check_code: 上一步返回的 _check_code
    """
    # 允许 docs_read → validate（手写代码）或 rendered → validate（模板生成）
    if _state == "docs_read":
        err = _check("pine_validate", "docs_read", check_code)
    elif _state == "rendered":
        err = _check("pine_validate", "rendered", check_code)
    else:
        return {"error": f"⛔ 顺序错误：当前状态是「{_state}」，需先调 pine_read_docs"}

    if err:
        return err

    try:
        result = _validate_code(code)
        _transit("validated", "va")
        return {
            "pass": result["pass"],
            "issues": result["issues"],
            "_check_code": _next_code,
            "_next_step": "pine_write",
        }
    except Exception as e:
        return {"pass": False, "issues": [{"rule": f"验证异常: {e}", "severity": "error"}]}


@mcp.tool()
def pine_write(check_code: str, code: str, filename: str) -> dict:
    """Step 4 — 将 Pine Script 代码写入 ~/Downloads/ 目录。

    必须先调 pine_validate 拿到 _check_code 传入。
    check_code: 上一步返回的 _check_code
    filename: 文件名（不含 .md 后缀）
    """
    err = _check("pine_write", "validated", check_code)
    if err:
        return err

    try:
        result = _write_pine(code, filename)
        _transit("done", "dn")
        return {
            "path": result["path"],
            "size": result["size"],
            "_check_code": _next_code,
            "_message": "✅ 文件已写入。本轮流程完成，可开始新一轮（重新调 pine_read_docs）。",
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
