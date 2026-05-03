/**
 * gene-crossover - Genetic crossover operator for GEP gene pool
 *
 * Combines strategies and signals from two high-performing parent genes
 * to create hybrid offspring, increasing diversity and breaking stagnation.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DEFAULT_GENES_PATH = path.join(
  process.env.HOME || '/tmp',
  '.claude/evolver/assets/gep/genes.json'
);

/**
 * Calculate fitness score for a gene based on epigenetic boosts
 * and category weighting (innovate genes get a diversity bonus).
 */
function fitnessScore(gene) {
  let score = 0.5; // base fitness

  // Epigenetic boost accumulation
  if (gene.epigenetic_marks && gene.epigenetic_marks.length > 0) {
    for (const mark of gene.epigenetic_marks) {
      score += (mark.boost || 0);
    }
  }

  // Category diversity bonus: innovate genes get +0.1
  if (gene.category === 'innovate') score += 0.1;

  // Signal breadth bonus: more signals = more versatile
  const signalCount = (gene.signals_match || []).length;
  score += Math.min(signalCount * 0.02, 0.15);

  // Strategy depth bonus: more steps = richer knowledge
  const strategyCount = (gene.strategy || []).length;
  score += Math.min(strategyCount * 0.01, 0.1);

  return Math.max(0, Math.min(1.0, score));
}

/**
 * Select the two best parent genes by fitness score.
 * Excludes retired genes. Requires at least 2 active genes.
 */
function selectParents(genes) {
  if (!genes || genes.length < 2) {
    throw new Error('Need at least 2 active genes for crossover');
  }

  const ranked = genes
    .map(g => ({ gene: g, fitness: fitnessScore(g) }))
    .sort((a, b) => b.fitness - a.fitness);

  return {
    parentA: ranked[0],
    parentB: ranked[1],
    fitnessReport: ranked.map(r => ({
      id: r.gene.id,
      category: r.gene.category,
      fitness: Math.round(r.fitness * 1000) / 1000,
      signals: (r.gene.signals_match || []).length,
      strategies: (r.gene.strategy || []).length
    }))
  };
}

/**
 * Perform crossover: combine two parent genes into a hybrid offspring.
 *
 * Strategy: alternating selection (step 1 from A, step 2 from B, etc.)
 * Signals: union with deduplication
 * Constraints: take the stricter (lower max_files)
 */
function crossover(geneA, geneB, opts = {}) {
  const timestamp = opts.timestamp || Date.now();
  const shortHash = crypto.createHash('sha256')
    .update(`${geneA.id}+${geneB.id}@${timestamp}`)
    .digest('hex')
    .slice(0, 8);
  const childId = opts.childId || `gene_hybrid_${shortHash}`;

  // Alternating strategy crossover
  const stepsA = geneA.strategy || [];
  const stepsB = geneB.strategy || [];
  const maxLen = Math.max(stepsA.length, stepsB.length);
  const childStrategy = [];
  const seen = new Set();

  for (let i = 0; i < maxLen; i++) {
    const step = (i % 2 === 0)
      ? (stepsA[i] || stepsB[i])
      : (stepsB[i] || stepsA[i]);
    if (step && !seen.has(step)) {
      seen.add(step);
      childStrategy.push(step);
    }
  }

  // Signal union with deduplication
  const signalSet = new Set([
    ...(geneA.signals_match || []),
    ...(geneB.signals_match || [])
  ]);
  const childSignals = [...signalSet];

  // Stricter constraints
  const maxFilesA = (geneA.constraints || {}).max_files || 20;
  const maxFilesB = (geneB.constraints || {}).max_files || 20;
  const forbiddenA = (geneA.constraints || {}).forbidden_paths || [];
  const forbiddenB = (geneB.constraints || {}).forbidden_paths || [];
  const forbiddenSet = new Set([...forbiddenA, ...forbiddenB]);

  // Merge preconditions
  const preA = geneA.preconditions || [];
  const preB = geneB.preconditions || [];
  const precondSet = new Set([...preA, ...preB]);

  // Combine validation steps
  const valA = geneA.validation || [];
  const valB = geneB.validation || [];
  const valSet = new Set([...valA, ...valB]);

  const offspring = {
    type: 'Gene',
    schema_version: '1.6.0',
    id: childId,
    category: 'innovate',
    signals_match: childSignals,
    preconditions: [...precondSet],
    strategy: childStrategy,
    constraints: {
      max_files: Math.min(maxFilesA, maxFilesB),
      forbidden_paths: [...forbiddenSet]
    },
    validation: [...valSet],
    epigenetic_marks: [
      {
        context: `crossover:${geneA.id}+${geneB.id}`,
        boost: 0.15,
        reason: 'hybrid_vigor_initial_boost',
        created_at: new Date(timestamp).toISOString()
      }
    ],
    registered_at: new Date(timestamp).toISOString(),
    registered_by: 'gene-crossover-skill'
  };

  return offspring;
}

/**
 * Main entry: load genes, select parents, produce offspring.
 */
async function main(opts = {}) {
  const genesPath = opts.genesPath || DEFAULT_GENES_PATH;
  const resolvedPath = genesPath.replace(/^~/, process.env.HOME || '/tmp');

  let data;
  try {
    const raw = fs.readFileSync(resolvedPath, 'utf8');
    data = JSON.parse(raw);
  } catch (e) {
    return {
      error: `Cannot read genes: ${e.message}`,
      offspring: null,
      parents: null,
      fitnessReport: []
    };
  }

  const activeGenes = data.genes || [];

  if (activeGenes.length < 2) {
    return {
      error: 'Need at least 2 active genes for crossover',
      offspring: null,
      parents: null,
      fitnessReport: [],
      activeGeneCount: activeGenes.length
    };
  }

  const { parentA, parentB, fitnessReport } = selectParents(activeGenes);
  const offspring = crossover(parentA.gene, parentB.gene);

  return {
    offspring,
    parents: {
      a: { id: parentA.gene.id, fitness: parentA.fitness },
      b: { id: parentB.gene.id, fitness: parentB.fitness }
    },
    fitnessReport,
    activeGeneCount: activeGenes.length,
    diversityGain: {
      signalsBefore: Math.max(
        (parentA.gene.signals_match || []).length,
        (parentB.gene.signals_match || []).length
      ),
      signalsAfter: offspring.signals_match.length,
      strategiesBefore: Math.max(
        (parentA.gene.strategy || []).length,
        (parentB.gene.strategy || []).length
      ),
      strategiesAfter: offspring.strategy.length
    }
  };
}

module.exports = { main, selectParents, crossover, fitnessScore };
