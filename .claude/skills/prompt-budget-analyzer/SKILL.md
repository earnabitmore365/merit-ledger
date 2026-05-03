---
name: prompt-budget-analyzer
description: Analyze GEP prompt composition, track section size trends across evolution cycles, and identify bloat sources. Use when prompt is growing too large, when optimizing context injection, or when diagnosing stagnation caused by token budget pressure.
---

# Prompt Budget Analyzer

Breaks down GEP evolution prompts into sections and measures how much space each uses.

## When to Use

- After multiple optimize cycles to check if prompt is shrinking
- When stagnation is detected (prompt bloat can degrade LLM performance)
- Before/after narrative compression to verify improvement
- Periodic health check on context injection efficiency

## Usage

```bash
node ~/.claude/skills/prompt-budget-analyzer/index.js
```

Or programmatically:

```js
const { main } = require('~/.claude/skills/prompt-budget-analyzer');
const result = await main({ limit: 10 }); // analyze last 10 prompts
```

## Options

- `limit` (number, default 10): How many recent prompt files to analyze
- `dir` (string): Override evolution directory path

## Output

- Section breakdown table (lines, bytes, % of total)
- Growth trends (first vs latest prompt comparison)
- Top bloat sources ranked by absolute growth
- Compression recommendations for sections >15% of budget

## Sections Tracked

Protocol Header, Signals, Env Fingerprint, Innovation Catalyst, Gene Preview,
Capsule Preview, Capability Candidates, Evolution Narrative, Execution Context, Post-solidify Tail.
