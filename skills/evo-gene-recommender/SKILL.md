---
name: evo-gene-recommender
description: Recommend optimal evolution genes for given signals based on historical performance data. Use when selecting genes for evolution cycles, diagnosing gene selection issues, or comparing gene fitness for specific signal patterns.
---

# evo-gene-recommender

Analyzes evolution event history to recommend which gene best fits a given set of signals.

## Usage

```bash
# Recommend genes for specific signals
node index.js protocol_drift evolution_stagnation_detected

# Recommend genes for default signals (protocol_drift + stagnation)
node index.js
```

## Output

Returns JSON with:
- **recommendations**: Top-N genes ranked by composite score (signal affinity × 0.4 + success rate × 0.3 + avg score × 0.2 + experience bonus × 0.1)
- **warnings**: Genes flagged as retired, low success rate, or high failure count
- **summary**: One-line recommendation

## Programmatic API

```javascript
const { recommend } = require('./index');

const result = recommend(['protocol_drift', 'user_feature_request'], {
  topN: 5,
  excludeGenes: ['gene_auto_53538cc4'],
  intentFilter: 'innovate'
});
```

## Scoring

| Weight | Factor | Description |
|--------|--------|-------------|
| 40% | Signal affinity | How many query signals match the gene's historical signal set |
| 30% | Success rate | Proportion of successful uses |
| 20% | Average score | Mean outcome score across uses |
| 10% | Experience bonus | Bonus for genes used 3+ times (proven track record) |
