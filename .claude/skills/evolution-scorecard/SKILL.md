---
name: evolution-scorecard
description: Compute a quantitative 0-100 health score for the evolution system with metric breakdown. Use when checking evolution health, comparing across time periods, or diagnosing systemic issues beyond individual cycle results.
---

# Evolution Scorecard

Computes a single composite health score (0-100) by aggregating six weighted metrics:

| Metric | Weight | What it measures |
|--------|--------|-----------------|
| Success Rate | 25% | Recent cycle pass rate (last 20 cycles) |
| Innovation Ratio | 20% | Proportion of innovate-intent cycles |
| Zero-Change Rate | 20% | Inverse of empty/no-change cycles |
| Gene Diversity | 15% | How many distinct genes are actively used |
| Stagnation Freq | 10% | How often stagnation signals appear |
| Velocity | 10% | Average lines changed per successful cycle |

## Usage

```js
const { main } = require('./skills/evolution-scorecard');
const result = await main({ window: 20 }); // last 20 cycles
// result.score       → 0-100 composite score
// result.breakdown   → per-metric scores
// result.grade       → A/B/C/D/F letter grade
// result.recommendations → actionable improvement tips
```

## Output Example

```
Evolution Scorecard: 72/100 (B)
├─ Success Rate:     85/100 (17/20 passed)
├─ Innovation Ratio: 60/100 (6/20 innovate)
├─ Zero-Change Rate: 90/100 (2/20 empty)
├─ Gene Diversity:   55/100 (4/10 genes used)
├─ Stagnation Freq:  70/100 (3 stagnation signals)
└─ Velocity:         68/100 (avg 45 lines/cycle)
```
