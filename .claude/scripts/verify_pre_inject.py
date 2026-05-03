#!/usr/bin/env python3
"""
层3：Claude Code UserPromptSubmit hook — 开工前注入 verify --pre 状态
当 cwd 在 wuji-auto-trading，自动跑 wuji-verify --pre 的快速版（只扫反模式）
把违规数注入到系统提示，让白纱开工前就知道当前项目有多少违规。
"""

import json
import os
import subprocess
import sys

PROJ = "/Volumes/SSD-2TB/project/wuji-auto-trading"
VERIFY = os.path.join(PROJ, "wuji-verify.py")

AUTO_TRADING_MARKERS = ["wuji-auto-trading", "auto-trading"]


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    cwd = data.get("cwd", "") or os.getcwd()
    if not any(m in cwd for m in AUTO_TRADING_MARKERS):
        sys.exit(0)  # 不在 auto-trading 项目，跳过

    # 跑 verify --pre，结果直接注入 prompt（纯文本，无论有没有违规都显示）
    try:
        result = subprocess.run(
            ["python3", VERIFY, "--pre"],
            capture_output=True, text=True, timeout=30,
            cwd=PROJ
        )
        output = result.stdout.strip()
        if not output:
            sys.exit(0)

        lines = output.splitlines()
        violations = [l for l in lines if "❌" in l or "⚠️" in l]

        if violations:
            summary = f"【wuji-verify --pre】{len(violations)} 条违规：\n" + "\n".join(violations[:5])
            if len(violations) > 5:
                summary += f"\n...还有 {len(violations)-5} 条"
        else:
            summary = "【wuji-verify --pre】✅ 无反模式违规，开工吧"

        # stdout 纯文本直接注入 prompt
        print(summary)
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
