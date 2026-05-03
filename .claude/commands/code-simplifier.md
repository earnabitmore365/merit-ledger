---
description: Code Simplifier — simplify and refine recently modified code for clarity and maintainability, preserving all functionality
---

Launch an Explore agent to review recently modified Python files, then fix any simplification opportunities found.

## Scope

Review the 4 core merit/hook files:
1. `~/.claude/merit/merit_gate.py`
2. `~/.claude/merit/credit_manager.py`
3. `~/.claude/scripts/session_start.py`
4. `~/.claude/scripts/pre_compact_save.py`

## Review Criteria

Use the Agent tool (subagent_type: Explore, model: sonnet) to scan for:

1. **Unnecessary nesting** — flatten with early returns or guard clauses
2. **Redundant code** — duplicated blocks that should be a single function call
3. **Poor naming** — variables/functions that don't describe their purpose
4. **Unnecessary comments** — comments that describe what obvious code does (keep WHY comments)
5. **Overly complex expressions** — break into named intermediate variables
6. **Dead code** — unreachable branches, unused variables, stale imports

## Rules

- **Preserve all functionality** — only change HOW, never WHAT
- **No new features** — simplify, don't extend
- **No style-only changes** — must materially improve readability
- If the code is already clean, report "CLEAN" and stop

## After Review

Fix each finding directly. Summarize what was changed (or confirm clean).
