---
name: evo-cycle-guard
description: Pre-flight validator for proposed evolution cycles. Checks intent-mutation consistency, repeat detection, gene cooldown, innovation enforcement, signal cleanliness, and retired gene usage BEFORE execution. Use before starting any evolution cycle to prevent protocol violations and wasted cycles.
---

# evo-cycle-guard

Pre-flight gate that validates a proposed evolution cycle before execution.

## Checks Performed

| Check | Severity | What It Catches |
|-------|----------|-----------------|
| `intent_mutation_mismatch` | critical | mutation.category != event.intent |
| `retired_gene` | critical | Selecting a retired gene |
| `failure_streak` | critical | Gene failed 2+ times in recent window |
| `repeat_pattern` | high | Same gene+intent combo used 2+ times recently |
| `gene_cooldown` | high | Gene used 3+ times in last N cycles |
| `innovation_drought` | high | 3+ consecutive non-innovate cycles |
| `intent_gene_category_mismatch` | high | Intent doesn't match gene's category |
| `signal_pollution` | medium-high | Raw user messages or long signals |
| `unknown_gene` | medium | Gene ID not found in genes.json |

## Usage

```js
const guard = require('evo-cycle-guard');

const result = await guard.main({
  gene: 'gene_gep_optimize_prompt_and_assets',
  intent: 'optimize',
  signals: ['protocol_drift', 'user_improvement_suggestion'],
  mutationCategory: 'optimize',
  window: 5,
  quiet: false
});

if (!result.go) {
  console.log('BLOCKED:', result.blocks);
}
```

## Output

- `go: true` — safe to proceed (may have warnings)
- `go: false` — blocked, must change gene/intent/signals
- `blocks[]` — critical/high issues that prevent execution
- `warnings[]` — non-blocking issues to be aware of
