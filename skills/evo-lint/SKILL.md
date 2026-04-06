---
name: evo-lint
description: Validate evolution data integrity — chronological order, intent-gene consistency, signal cleanliness, gene reference integrity, and duplicate detection. Use when protocol_drift signals appear or before solidify to catch issues early.
---

# evo-lint

Lints evolution data files (narrative, genes.json) for common integrity issues that cause protocol_drift signals.

## Usage

```js
const { main, lintNarrative, lintGenes } = require('./skills/evo-lint');

// Full lint (reads from default paths)
const report = await main();
// report = { issues: [...], summary: { total, critical, warning, info } }

// Custom paths
const report = await main({
  narrativePath: '~/.claude/evolver/evolution/evolution_narrative.md',
  genesPath: '~/.claude/evolver/assets/gep/genes.json'
});
```

## Checks

| ID | Severity | Description |
|----|----------|-------------|
| CHRONO_ORDER | critical | Narrative entries out of chronological order |
| INTENT_MISMATCH | critical | INNOVATE/OPTIMIZE/REPAIR label doesn't match gene category |
| SIGNAL_POLLUTION | warning | Signal string >80 chars (likely raw user message leaked) |
| GENE_REF_MISSING | warning | Gene ID in narrative not found in genes.json (active or retired) |
| DUPLICATE_TIMESTAMP | info | Multiple entries with identical timestamp |
| DUPLICATE_SCOPE | info | Adjacent entries with identical gene+scope+result |

## When to trigger

- Before solidify to catch issues early
- When protocol_drift signals appear repeatedly
- After manual narrative edits
- As part of evo-doctor health checks
