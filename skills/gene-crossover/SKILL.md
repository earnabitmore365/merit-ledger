---
name: gene-crossover
description: Genetic crossover operator for GEP gene pool. Combines strategies and signals from two high-performing parent genes to create hybrid offspring genes, increasing diversity and breaking stagnation plateaus. Use when evolution_stagnation_detected or gene pool diversity is low.
---

# Gene Crossover

Implements biological genetic crossover for the GEP evolution engine.

## When to Use

- `evolution_stagnation_detected` signal is present
- Gene pool diversity score is low (Shannon entropy < 1.0)
- Same genes keep being selected cycle after cycle
- Want to explore new strategy combinations without manual gene authoring

## How It Works

1. **Select Parents**: Picks two genes with highest composite fitness (success rate × epigenetic boost)
2. **Crossover Strategies**: Combines strategy steps from both parents (alternating selection)
3. **Merge Signals**: Union of both parents' signal coverage with deduplication
4. **Inherit Constraints**: Takes the stricter constraint set (lower max_files)
5. **Mark Lineage**: Records parent IDs in epigenetic marks for genealogy tracking

## Output

Returns a new Gene object ready for registration in genes.json, plus a fitness report of parent candidates.

## API

```js
const { main, selectParents, crossover, fitnessScore } = require('./');

// Full run: analyze gene pool + produce offspring
const result = await main({ genesPath: '~/.claude/evolver/assets/gep/genes.json' });
// result.offspring - the new hybrid Gene object
// result.parents - selected parent genes
// result.fitnessReport - all genes ranked by fitness

// Manual crossover of two specific genes
const child = crossover(geneA, geneB, { childId: 'gene_hybrid_001' });
```
