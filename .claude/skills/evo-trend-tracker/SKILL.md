---
name: evo-trend-tracker
description: Track evolution metrics over time with rolling windows and linear regression trend detection. Shows whether success rate, innovation ratio, blast radius, and gene diversity are improving, degrading, or flat. Use when analyzing evolution momentum, diagnosing sustained performance shifts, or comparing periods.
---

# evo-trend-tracker

Time-series trend analysis of evolution metrics from `evolution_narrative.md`.

## What it does

- Parses all narrative entries into structured time-series data
- Computes rolling-window metrics (success rate, innovation ratio, avg blast radius, zero-change rate, gene diversity)
- Fits linear regression per metric to detect trend direction (improving / degrading / flat)
- Reports overall system momentum and per-metric breakdowns

## When to use

- Diagnosing whether the system is getting better or worse over time
- Comparing evolution performance across different periods
- Identifying which specific metrics are degrading before they become critical

## Usage

```javascript
const { main } = require('./skills/evo-trend-tracker');
const result = await main({ windowSize: 5 });
```

### Options

| Param | Default | Description |
|-------|---------|-------------|
| `narrativePath` | `~/.claude/evolver/evolution/evolution_narrative.md` | Path to narrative file |
| `windowSize` | `5` | Entries per rolling window |

### Output structure

```json
{
  "totalEntries": 45,
  "windowSize": 5,
  "dateRange": { "first": "2026-03-12", "last": "2026-03-27" },
  "current": {
    "count": 5,
    "successRate": 60,
    "innovationRatio": 40,
    "avgLines": 12.5,
    "zeroChangeRate": 20,
    "geneDiversity": 2
  },
  "windows": [ "..." ],
  "trends": {
    "successRate": { "slope": -2.3, "r2": 0.65, "direction": "degrading" },
    "innovationRatio": { "slope": 0.5, "r2": 0.12, "direction": "flat" }
  },
  "overall": "degrading",
  "summary": "1 improving, 2 degrading, 2 flat metrics. Overall: degrading."
}
```

### Exports

- `main(opts)` - Full analysis (async)
- `parseEntries(content)` - Parse narrative text into entry objects
- `windowMetrics(entries)` - Compute metrics for an entry array
- `linearRegression(values)` - Fit linear regression to number array
- `computeTrends(entries, windowSize)` - Rolling window trend computation
