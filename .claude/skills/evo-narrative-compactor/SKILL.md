---
name: evo-narrative-compactor
description: Automatically compresses evolution_narrative.md by consolidating adjacent same-gene entries into CONSOLIDATED blocks. Use when narrative grows long, optimize cycles are spent on manual compression, or protocol_drift signals from narrative bloat.
---

# evo-narrative-compactor

Automates narrative compression that previously consumed manual optimize cycles.

## Usage

```js
const compactor = require('./');

// Dry run (default) - shows what would be compressed
const report = await compactor.main();
// { groups: [...], dryRun: true, beforeLines: 84, afterLines: 62, saved: 22 }

// Apply mode - writes compressed narrative
const result = await compactor.main({ apply: true });

// Custom paths
await compactor.main({ narrativePath: '/path/to/narrative.md' });
```

## Compression Rules

1. Groups 3+ adjacent entries with the same gene into CONSOLIDATED blocks
2. Preserves the first and last entry timestamps in the range
3. Summarizes success/fail counts and total scope
4. Never removes ARCHIVED or existing CONSOLIDATED blocks
5. Preserves all non-entry content (headers, notes, blank lines)
6. Respects append-only: consolidation creates a summary, original data is in git history
