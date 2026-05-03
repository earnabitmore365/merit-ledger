'use strict';

const fs = require('fs');
const path = require('path');

const EVOLVER_DIR = path.join(process.env.HOME, '.claude', 'evolver');
const NARRATIVE_PATH = path.join(EVOLVER_DIR, 'evolution', 'evolution_narrative.md');
const GENES_PATH = path.join(EVOLVER_DIR, 'assets', 'gep', 'genes.json');

/**
 * Parse evolution_narrative.md into structured cycle entries.
 * Returns array of { date, intent, status, gene, score, scope, signals }
 */
function parseNarrative(text) {
  const entries = [];
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const headerMatch = line.match(/^### \[(\d{4}-\d{2}-\d{2}[^\]]*)\] (\w+) - (\w+)/);
    if (!headerMatch) continue;
    const entry = {
      date: headerMatch[1],
      intent: headerMatch[2].toLowerCase(),
      status: headerMatch[3].toLowerCase(),
      gene: null,
      score: null,
      scope: { files: 0, lines: 0 },
      signals: []
    };
    for (let j = i + 1; j < lines.length && !lines[j].startsWith('###') && !lines[j].startsWith('>'); j++) {
      const detail = lines[j];
      const geneMatch = detail.match(/Gene:\s*([\w.-]+)/);
      if (geneMatch) entry.gene = geneMatch[1];
      const scoreMatch = detail.match(/Score:\s*([\d.]+)/);
      if (scoreMatch) entry.score = parseFloat(scoreMatch[1]);
      const scopeMatch = detail.match(/Scope:\s*(\d+)\s*files?,\s*(\d+)\s*lines?/);
      if (scopeMatch) {
        entry.scope.files = parseInt(scopeMatch[1]);
        entry.scope.lines = parseInt(scopeMatch[2]);
      }
      const sigMatch = detail.match(/Signals:\s*\[([^\]]*)\]/);
      if (sigMatch) {
        entry.signals = sigMatch[1].split(',').map(s => s.trim()).filter(Boolean);
      }
    }
    entries.push(entry);
  }
  return entries;
}

/**
 * Load gene pool from genes.json.
 */
function loadGenes() {
  try {
    const data = JSON.parse(fs.readFileSync(GENES_PATH, 'utf8'));
    return {
      active: (data.genes || []).map(g => g.id),
      retired: (data.retired_genes || []).map(g => g.id),
      geneMap: Object.fromEntries((data.genes || []).map(g => [g.id, g]))
    };
  } catch {
    return { active: [], retired: [], geneMap: {} };
  }
}

/**
 * Check for raw user messages in signals (signal pollution).
 */
function checkSignalCleanliness(signals) {
  const issues = [];
  for (const sig of signals) {
    if (sig.length > 80) {
      issues.push({ type: 'signal_too_long', signal: sig.slice(0, 60) + '...', severity: 'high' });
    }
    if (/[\u4e00-\u9fff]/.test(sig) && !sig.startsWith('user_feature_request:')) {
      issues.push({ type: 'raw_user_message', signal: sig.slice(0, 40), severity: 'high' });
    }
    if (/\s{3,}/.test(sig) || sig.includes('\n')) {
      issues.push({ type: 'whitespace_pollution', signal: sig.slice(0, 40), severity: 'medium' });
    }
  }
  return issues;
}

/**
 * Main pre-flight check for a proposed evolution cycle.
 *
 * @param {Object} opts
 * @param {string} opts.gene - Proposed gene ID
 * @param {string} opts.intent - Proposed intent (repair|optimize|innovate)
 * @param {string[]} opts.signals - Proposed signals
 * @param {string} [opts.mutationCategory] - Mutation category (should match intent)
 * @param {number} [opts.window=5] - How many recent cycles to check
 * @param {boolean} [opts.quiet=false] - Suppress console output
 * @returns {Promise<Object>} { go: bool, blocks: [], warnings: [], recommendation: string }
 */
async function main(opts = {}) {
  const { gene, intent, signals = [], mutationCategory, window: win = 5, quiet = false } = opts;
  const blocks = [];
  const warnings = [];

  let narrative = '';
  try { narrative = fs.readFileSync(NARRATIVE_PATH, 'utf8'); } catch {}
  const entries = parseNarrative(narrative);
  const recent = entries.slice(-win);
  const genePool = loadGenes();

  // 1. Intent-Mutation consistency
  if (mutationCategory && intent && mutationCategory !== intent) {
    blocks.push({
      check: 'intent_mutation_mismatch',
      detail: `intent="${intent}" but mutation.category="${mutationCategory}"`,
      severity: 'critical'
    });
  }

  // 2. Retired gene check
  if (gene && genePool.retired.includes(gene)) {
    blocks.push({
      check: 'retired_gene',
      detail: `Gene "${gene}" is retired and should not be selected`,
      severity: 'critical'
    });
  }

  // 3. Gene not in active pool
  if (gene && !genePool.active.includes(gene) && !genePool.retired.includes(gene)) {
    warnings.push({
      check: 'unknown_gene',
      detail: `Gene "${gene}" not found in genes.json`,
      severity: 'medium'
    });
  }

  // 4. Repeat detection (same gene+intent in recent cycles)
  if (gene && intent) {
    const repeats = recent.filter(e => e.gene === gene && e.intent === intent);
    if (repeats.length >= 2) {
      blocks.push({
        check: 'repeat_pattern',
        detail: `Gene "${gene}" + intent "${intent}" used ${repeats.length}x in last ${win} cycles`,
        severity: 'high'
      });
    } else if (repeats.length === 1) {
      warnings.push({
        check: 'recent_use',
        detail: `Gene "${gene}" + intent "${intent}" used 1x in last ${win} cycles`,
        severity: 'low'
      });
    }
  }

  // 5. Gene cooldown (gene used too frequently regardless of intent)
  if (gene) {
    const geneUses = recent.filter(e => e.gene === gene);
    if (geneUses.length >= 3) {
      blocks.push({
        check: 'gene_cooldown',
        detail: `Gene "${gene}" used ${geneUses.length}x in last ${win} cycles — needs cooldown`,
        severity: 'high'
      });
    }
  }

  // 6. Innovation enforcement (3+ consecutive non-innovate)
  const lastN = entries.slice(-3);
  const allNonInnovate = lastN.length >= 3 && lastN.every(e => e.intent !== 'innovate');
  if (allNonInnovate && intent !== 'innovate') {
    blocks.push({
      check: 'innovation_drought',
      detail: `Last ${lastN.length} cycles were all non-innovate — innovate intent required`,
      severity: 'high'
    });
  }

  // 7. Signal cleanliness
  const signalIssues = checkSignalCleanliness(signals);
  for (const issue of signalIssues) {
    warnings.push({
      check: `signal_${issue.type}`,
      detail: issue.signal,
      severity: issue.severity
    });
  }

  // 8. Intent-gene category consistency
  if (gene && intent && genePool.geneMap[gene]) {
    const geneCategory = genePool.geneMap[gene].category;
    if (geneCategory === 'optimize' && intent === 'innovate') {
      warnings.push({
        check: 'intent_gene_category_mismatch',
        detail: `Intent "innovate" but gene "${gene}" category is "optimize"`,
        severity: 'high'
      });
    }
    if (geneCategory === 'repair' && intent === 'innovate') {
      warnings.push({
        check: 'intent_gene_category_mismatch',
        detail: `Intent "innovate" but gene "${gene}" category is "repair"`,
        severity: 'high'
      });
    }
  }

  // 9. Recent failure streak detection
  if (gene) {
    const recentWithGene = recent.filter(e => e.gene === gene);
    const recentFails = recentWithGene.filter(e => e.status === 'failed');
    if (recentFails.length >= 2) {
      blocks.push({
        check: 'failure_streak',
        detail: `Gene "${gene}" failed ${recentFails.length}x in last ${win} cycles — switch gene`,
        severity: 'critical'
      });
    }
  }

  const hasBlocks = blocks.length > 0;
  const go = !hasBlocks;

  let recommendation = '';
  if (go && warnings.length === 0) {
    recommendation = 'All clear — proceed with proposed cycle.';
  } else if (go) {
    recommendation = `Proceed with caution — ${warnings.length} warning(s) detected.`;
  } else {
    const blockChecks = blocks.map(b => b.check).join(', ');
    recommendation = `BLOCKED — ${blocks.length} issue(s): ${blockChecks}. Change gene, intent, or signals.`;
  }

  const result = { go, blocks, warnings, recommendation, recentCycles: recent.length, totalCycles: entries.length };

  if (!quiet) {
    const icon = go ? '✅' : '🚫';
    console.log(`${icon} evo-cycle-guard: ${recommendation}`);
    if (blocks.length > 0) {
      console.log('  BLOCKS:');
      for (const b of blocks) console.log(`    [${b.severity}] ${b.check}: ${b.detail}`);
    }
    if (warnings.length > 0) {
      console.log('  WARNINGS:');
      for (const w of warnings) console.log(`    [${w.severity}] ${w.check}: ${w.detail}`);
    }
  }

  return result;
}

module.exports = { main, parseNarrative, loadGenes, checkSignalCleanliness };
