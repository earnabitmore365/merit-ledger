/**
 * evolution-scorecard: Quantitative health score (0-100) for the evolution system.
 *
 * Aggregates six weighted metrics from evolution_narrative.md and genes.json
 * into a single trackable composite score with letter grade and recommendations.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const DEFAULTS = {
  narrativePath: path.join(os.homedir(), '.claude/evolver/evolution/evolution_narrative.md'),
  genesPath: path.join(os.homedir(), '.claude/evolver/assets/gep/genes.json'),
  window: 20,
};

const WEIGHTS = {
  successRate: 0.25,
  innovationRatio: 0.20,
  zeroChangeRate: 0.20,
  geneDiversity: 0.15,
  stagnationFreq: 0.10,
  velocity: 0.10,
};

function readFileOrNull(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}

/**
 * Parse narrative entries from evolution_narrative.md
 */
function parseEntries(content) {
  if (!content) return [];
  const entries = [];
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const hdr = lines[i].match(
      /^### \[(\d{4}-\d{2}-\d{2}[\sT][\d:]+(?:\.\d+)?)\]\s+(INNOVATE|OPTIMIZE|REPAIR)\s+-\s+(success|failed)/i
    );
    if (!hdr) continue;

    const entry = { date: hdr[1], intent: hdr[2].toUpperCase(), outcome: hdr[3].toLowerCase(), gene: null, score: 0, scope: { files: 0, lines: 0 }, signals: [] };

    // Parse detail lines below the header
    for (let j = i + 1; j < Math.min(i + 6, lines.length); j++) {
      const l = lines[j];
      if (l.startsWith('### ')) break;

      const geneMatch = l.match(/Gene:\s*(gene_\S+)/);
      if (geneMatch) entry.gene = geneMatch[1];

      const scoreMatch = l.match(/Score:\s*([\d.]+)/);
      if (scoreMatch) entry.score = parseFloat(scoreMatch[1]);

      const scopeMatch = l.match(/Scope:\s*(\d+)\s*files?,\s*(\d+)\s*lines?/);
      if (scopeMatch) {
        entry.scope.files = parseInt(scopeMatch[1]);
        entry.scope.lines = parseInt(scopeMatch[2]);
      }

      const sigMatch = l.match(/Signals:\s*\[([^\]]+)\]/);
      if (sigMatch) entry.signals = sigMatch[1].split(',').map(s => s.trim());
    }

    entries.push(entry);
  }

  return entries;
}

/**
 * Load active gene count from genes.json
 */
function loadGenePool(genesPath) {
  const raw = readFileOrNull(genesPath);
  if (!raw) return { active: 0, retired: 0, total: 0 };
  try {
    const data = JSON.parse(raw);
    const genes = data.genes || data;
    const active = Array.isArray(genes) ? genes.length : 0;
    const retired = Array.isArray(data.retired_genes) ? data.retired_genes.length : 0;
    return { active, retired, total: active + retired };
  } catch { return { active: 0, retired: 0, total: 0 }; }
}

/**
 * Compute individual metric scores (each 0-100)
 */
function computeMetrics(entries, genePool, window) {
  const recent = entries.slice(-window);
  const total = recent.length;
  if (total === 0) {
    return {
      successRate: { score: 0, detail: 'No cycles found' },
      innovationRatio: { score: 0, detail: 'No cycles found' },
      zeroChangeRate: { score: 0, detail: 'No cycles found' },
      geneDiversity: { score: 0, detail: 'No cycles found' },
      stagnationFreq: { score: 0, detail: 'No cycles found' },
      velocity: { score: 0, detail: 'No cycles found' },
    };
  }

  // 1. Success Rate: % of successful cycles
  const successes = recent.filter(e => e.outcome === 'success').length;
  const successRate = Math.round((successes / total) * 100);

  // 2. Innovation Ratio: % of innovate-intent cycles (target: 60%)
  const innovates = recent.filter(e => e.intent === 'INNOVATE').length;
  const innovPct = innovates / total;
  // Score peaks at 60% innovation, drops linearly outside [30%, 90%]
  const innovationRatio = Math.round(Math.min(100, Math.max(0, innovPct <= 0.6
    ? (innovPct / 0.6) * 100
    : 100 - ((innovPct - 0.6) / 0.4) * 50)));

  // 3. Zero-Change Rate: penalize cycles with 0 files changed
  const zeroChange = recent.filter(e => e.scope.files === 0 && e.scope.lines === 0).length;
  const zeroChangeRate = Math.round(Math.max(0, 100 - (zeroChange / total) * 200));

  // 4. Gene Diversity: how many distinct genes used relative to active pool
  const usedGenes = new Set(recent.filter(e => e.gene).map(e => e.gene));
  const diversityRatio = genePool.active > 0 ? usedGenes.size / genePool.active : 0;
  const geneDiversity = Math.round(Math.min(100, diversityRatio * 100));

  // 5. Stagnation Frequency: how many cycles have stagnation signals
  const stagnationCycles = recent.filter(e =>
    e.signals.some(s => s.includes('stagnation') || s.includes('plateau'))
  ).length;
  const stagnationFreq = Math.round(Math.max(0, 100 - (stagnationCycles / total) * 150));

  // 6. Velocity: average lines changed per successful cycle (capped at 200 for max score)
  const successfulEntries = recent.filter(e => e.outcome === 'success' && e.scope.lines > 0);
  const avgLines = successfulEntries.length > 0
    ? successfulEntries.reduce((sum, e) => sum + e.scope.lines, 0) / successfulEntries.length
    : 0;
  const velocity = Math.round(Math.min(100, (avgLines / 200) * 100));

  return {
    successRate: { score: successRate, detail: `${successes}/${total} passed` },
    innovationRatio: { score: innovationRatio, detail: `${innovates}/${total} innovate (${Math.round(innovPct * 100)}%)` },
    zeroChangeRate: { score: zeroChangeRate, detail: `${zeroChange}/${total} empty` },
    geneDiversity: { score: geneDiversity, detail: `${usedGenes.size}/${genePool.active} genes used` },
    stagnationFreq: { score: stagnationFreq, detail: `${stagnationCycles} stagnation signals` },
    velocity: { score: velocity, detail: `avg ${Math.round(avgLines)} lines/cycle` },
  };
}

/**
 * Compute composite score and letter grade
 */
function computeComposite(metrics) {
  let composite = 0;
  for (const [key, weight] of Object.entries(WEIGHTS)) {
    composite += metrics[key].score * weight;
  }
  composite = Math.round(composite);

  let grade;
  if (composite >= 90) grade = 'A';
  else if (composite >= 80) grade = 'B+';
  else if (composite >= 70) grade = 'B';
  else if (composite >= 60) grade = 'C';
  else if (composite >= 50) grade = 'D';
  else grade = 'F';

  return { score: composite, grade };
}

/**
 * Generate actionable recommendations based on weak metrics
 */
function generateRecommendations(metrics) {
  const recs = [];
  if (metrics.successRate.score < 70) {
    recs.push('Success rate below 70%: review failing genes and consider retirement or strategy updates.');
  }
  if (metrics.innovationRatio.score < 50) {
    recs.push('Innovation ratio low: prioritize innovate-intent cycles to avoid maintenance stagnation.');
  }
  if (metrics.zeroChangeRate.score < 60) {
    recs.push('Too many zero-change cycles: audit gene preconditions and retire genes that cannot produce changes.');
  }
  if (metrics.geneDiversity.score < 50) {
    recs.push('Gene diversity low: try gene-crossover or create new specialized genes for underserved signals.');
  }
  if (metrics.stagnationFreq.score < 50) {
    recs.push('Frequent stagnation signals: consider adding new innovation catalyst ideas or expanding signal coverage.');
  }
  if (metrics.velocity.score < 40) {
    recs.push('Low velocity: cycles are producing few changes. Focus on higher-impact mutations.');
  }
  if (recs.length === 0) {
    recs.push('System health is good. Continue current evolution strategy.');
  }
  return recs;
}

/**
 * Main entry point
 * @param {Object} opts - { window: number, narrativePath: string, genesPath: string }
 * @returns {Promise<Object>} Scorecard result
 */
async function main(opts = {}) {
  const narrativePath = opts.narrativePath || DEFAULTS.narrativePath;
  const genesPath = opts.genesPath || DEFAULTS.genesPath;
  const window = opts.window || DEFAULTS.window;

  const narrativeContent = readFileOrNull(narrativePath);
  const entries = parseEntries(narrativeContent);
  const genePool = loadGenePool(genesPath);
  const metrics = computeMetrics(entries, genePool, window);
  const { score, grade } = computeComposite(metrics);
  const recommendations = generateRecommendations(metrics);

  return {
    score,
    grade,
    window,
    totalCycles: entries.length,
    analyzedCycles: Math.min(entries.length, window),
    genePool,
    breakdown: metrics,
    recommendations,
  };
}

module.exports = { main };
