---
name: evo-digest
description: Generate a human-readable evolution digest report for the boss. Use when the boss asks for evolution status, weekly summary, or wants to understand what the evolver has been doing.
---

# evo-digest

Generates concise, boss-friendly evolution digest reports from raw evolution data.

## Usage

```js
const { main, generateDigest, parseNarrative, calcMetrics } = require('./skills/evo-digest');

// Full digest (reads from default paths)
await main();

// Custom paths
await generateDigest({
  narrativePath: '~/.claude/evolver/evolution/evolution_narrative.md',
  memoryPath: '~/.claude/evolver/MEMORY.md',
  genesPath: '~/.claude/evolver/assets/gep/genes.json'
});
```

## Output

A structured markdown digest containing:
- Period summary (cycles count, success rate, innovation ratio)
- Top changes (what actually improved)
- Health indicators (stagnation risk, gene diversity, blast radius trend)
- Action items (what needs attention)

## When to trigger

- Boss asks "evolver 最近怎么样" / "进化摘要" / "evolution digest"
- Weekly review meetings
- After a series of evolution cycles to summarize progress
