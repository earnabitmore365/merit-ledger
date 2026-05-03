/**
 * evo-lint: Evolution data integrity linter
 *
 * Validates evolution_narrative.md and genes.json for:
 * - Chronological order violations
 * - Intent-gene category mismatches
 * - Signal pollution (raw user messages in signal fields)
 * - Gene reference integrity (missing genes)
 * - Duplicate entries
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const DEFAULTS = {
  narrativePath: path.join(os.homedir(), '.claude/evolver/evolution/evolution_narrative.md'),
  genesPath: path.join(os.homedir(), '.claude/evolver/assets/gep/genes.json'),
};

function readFileOrNull(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}

/**
 * Parse narrative headers into structured entries with line numbers
 */
function parseNarrativeEntries(content) {
  if (!content) return [];
  const entries = [];
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const headerMatch = line.match(
      /^### \[(\d{4}-\d{2}-\d{2}[\sT][\d:]+(?:\.\d+)?)\]\s+(INNOVATE|OPTIMIZE|REPAIR)\s+-\s+(success|failed)/i
    );
    if (!headerMatch) continue;

    const entry = {
      lineNum: i + 1,
      dateStr: headerMatch[1].trim(),
      date: new Date(headerMatch[1].trim().replace(' ', 'T')),
      intent: headerMatch[2].toUpperCase(),
      status: headerMatch[3].toLowerCase(),
      gene: null,
      scope: { files: 0, lines: 0 },
      signals: [],
      result: '',
    };

    // Parse subsequent lines for gene, signals, scope, result
    for (let j = i + 1; j < Math.min(i + 6, lines.length); j++) {
      const l = lines[j];
      if (l.startsWith('### ') || l.startsWith('> ')) break;

      const geneMatch = l.match(/Gene:\s+(gene_\S+)/);
      if (geneMatch) entry.gene = geneMatch[1];

      const scopeMatch = l.match(/Scope:\s+(\d+)\s+files?,\s+(\d+)\s+lines?/);
      if (scopeMatch) {
        entry.scope.files = parseInt(scopeMatch[1]);
        entry.scope.lines = parseInt(scopeMatch[2]);
      }

      const signalsMatch = l.match(/Signals:\s+\[([^\]]+)\]/);
      if (signalsMatch) {
        entry.signals = signalsMatch[1].split(',').map(s => s.trim());
      }

      const resultMatch = l.match(/Result:\s+(.+)/);
      if (resultMatch) entry.result = resultMatch[1].trim();
    }

    entries.push(entry);
  }
  return entries;
}

/**
 * Load gene registry (active + retired)
 */
function loadGeneRegistry(content) {
  if (!content) return { active: [], retired: [], allIds: new Set() };
  try {
    const data = JSON.parse(content);
    const active = (data.genes || []).map(g => ({ id: g.id, category: g.category }));
    const retired = (data.retired_genes || []).map(g => ({ id: g.id, category: g.category || g._retired_reason }));
    const allIds = new Set([...active.map(g => g.id), ...retired.map(g => g.id)]);
    return { active, retired, allIds };
  } catch {
    return { active: [], retired: [], allIds: new Set() };
  }
}

/**
 * Check: Chronological order
 */
function checkChronologicalOrder(entries) {
  const issues = [];
  for (let i = 1; i < entries.length; i++) {
    if (entries[i].date < entries[i - 1].date) {
      issues.push({
        check: 'CHRONO_ORDER',
        severity: 'critical',
        line: entries[i].lineNum,
        message: `Out of order: [${entries[i].dateStr}] appears after [${entries[i - 1].dateStr}]`,
        fix: `Move entry at line ${entries[i].lineNum} before entry at line ${entries[i - 1].lineNum}`,
      });
    }
  }
  return issues;
}

/**
 * Check: Intent-gene category consistency
 */
function checkIntentConsistency(entries, registry) {
  const issues = [];
  const intentToCategory = { INNOVATE: 'innovate', OPTIMIZE: 'optimize', REPAIR: 'repair' };

  for (const entry of entries) {
    if (!entry.gene) continue;
    const geneInfo = registry.active.find(g => g.id === entry.gene);
    if (!geneInfo) continue; // handled by gene ref check

    const expectedCategory = intentToCategory[entry.intent];
    if (geneInfo.category !== expectedCategory) {
      issues.push({
        check: 'INTENT_MISMATCH',
        severity: 'critical',
        line: entry.lineNum,
        message: `Intent ${entry.intent} but gene ${entry.gene} has category "${geneInfo.category}"`,
        fix: `Change intent to ${geneInfo.category.toUpperCase()} or use a ${expectedCategory} gene`,
      });
    }
  }
  return issues;
}

/**
 * Check: Signal pollution (raw user messages leaked into signals)
 */
function checkSignalPollution(entries) {
  const issues = [];
  const MAX_SIGNAL_LENGTH = 80;

  for (const entry of entries) {
    for (const signal of entry.signals) {
      if (signal.length > MAX_SIGNAL_LENGTH) {
        issues.push({
          check: 'SIGNAL_POLLUTION',
          severity: 'warning',
          line: entry.lineNum,
          message: `Signal too long (${signal.length} chars): "${signal.slice(0, 60)}..."`,
          fix: 'Truncate or replace with structured signal identifier',
        });
      }
    }
  }
  return issues;
}

/**
 * Check: Gene reference integrity
 */
function checkGeneReferences(entries, registry) {
  const issues = [];
  for (const entry of entries) {
    if (!entry.gene) continue;
    if (!registry.allIds.has(entry.gene)) {
      issues.push({
        check: 'GENE_REF_MISSING',
        severity: 'warning',
        line: entry.lineNum,
        message: `Gene "${entry.gene}" not found in genes.json (active or retired)`,
        fix: `Add to retired_genes if historical, or verify gene ID spelling`,
      });
    }
  }
  return issues;
}

/**
 * Check: Duplicate entries
 */
function checkDuplicates(entries) {
  const issues = [];
  const seen = new Map();

  for (const entry of entries) {
    // Duplicate timestamp
    if (seen.has(entry.dateStr)) {
      issues.push({
        check: 'DUPLICATE_TIMESTAMP',
        severity: 'info',
        line: entry.lineNum,
        message: `Duplicate timestamp: ${entry.dateStr} (also at line ${seen.get(entry.dateStr)})`,
        fix: 'Consolidate or archive duplicate entries',
      });
    }
    seen.set(entry.dateStr, entry.lineNum);
  }

  // Adjacent duplicate scope+gene
  for (let i = 1; i < entries.length; i++) {
    const a = entries[i - 1], b = entries[i];
    if (a.gene === b.gene && a.scope.files === b.scope.files &&
        a.scope.lines === b.scope.lines && a.result === b.result) {
      issues.push({
        check: 'DUPLICATE_SCOPE',
        severity: 'info',
        line: b.lineNum,
        message: `Identical to previous entry (same gene, scope, result)`,
        fix: 'Consolidate into archive block',
      });
    }
  }
  return issues;
}

/**
 * Run all lint checks
 */
function lintNarrative(narrativeContent, genesContent) {
  const entries = parseNarrativeEntries(narrativeContent);
  const registry = loadGeneRegistry(genesContent);

  const allIssues = [
    ...checkChronologicalOrder(entries),
    ...checkIntentConsistency(entries, registry),
    ...checkSignalPollution(entries),
    ...checkGeneReferences(entries, registry),
    ...checkDuplicates(entries),
  ];

  return {
    entriesScanned: entries.length,
    issues: allIssues,
    summary: {
      total: allIssues.length,
      critical: allIssues.filter(i => i.severity === 'critical').length,
      warning: allIssues.filter(i => i.severity === 'warning').length,
      info: allIssues.filter(i => i.severity === 'info').length,
    },
  };
}

/**
 * Lint genes.json for internal consistency
 */
function lintGenes(genesContent) {
  const issues = [];
  if (!genesContent) return { issues, summary: { total: 0, critical: 0, warning: 0, info: 0 } };

  let data;
  try { data = JSON.parse(genesContent); } catch (e) {
    return { issues: [{ check: 'INVALID_JSON', severity: 'critical', line: 0, message: `genes.json parse error: ${e.message}` }], summary: { total: 1, critical: 1, warning: 0, info: 0 } };
  }

  const genes = data.genes || [];
  const retired = data.retired_genes || [];
  const allIds = new Set();

  for (const g of genes) {
    if (allIds.has(g.id)) {
      issues.push({ check: 'DUPLICATE_GENE_ID', severity: 'critical', line: 0, message: `Duplicate active gene ID: ${g.id}` });
    }
    allIds.add(g.id);

    if (!g.category || !['repair', 'optimize', 'innovate'].includes(g.category)) {
      issues.push({ check: 'INVALID_CATEGORY', severity: 'warning', line: 0, message: `Gene ${g.id} has invalid category: "${g.category}"` });
    }

    if (!g.signals_match || g.signals_match.length === 0) {
      issues.push({ check: 'NO_SIGNALS', severity: 'warning', line: 0, message: `Gene ${g.id} has no signals_match` });
    }
  }

  // Check retired genes don't appear in active
  for (const r of retired) {
    if (genes.some(g => g.id === r.id)) {
      issues.push({ check: 'RETIRED_STILL_ACTIVE', severity: 'critical', line: 0, message: `Retired gene ${r.id} still appears in active genes array` });
    }
  }

  return {
    issues,
    summary: {
      total: issues.length,
      critical: issues.filter(i => i.severity === 'critical').length,
      warning: issues.filter(i => i.severity === 'warning').length,
      info: issues.filter(i => i.severity === 'info').length,
    },
  };
}

/**
 * Format report as readable text
 */
function formatReport(narrativeReport, genesReport) {
  const severityIcon = { critical: '🔴', warning: '🟡', info: '🔵' };
  const lines = ['# evo-lint Report', `> ${new Date().toISOString().slice(0, 19)}`, ''];

  lines.push(`## Narrative (${narrativeReport.entriesScanned} entries scanned)`);
  if (narrativeReport.issues.length === 0) {
    lines.push('  🟢 No issues found');
  } else {
    for (const issue of narrativeReport.issues) {
      lines.push(`  ${severityIcon[issue.severity]} [${issue.check}] L${issue.line}: ${issue.message}`);
      if (issue.fix) lines.push(`    → Fix: ${issue.fix}`);
    }
  }

  lines.push('', `## Genes`);
  if (genesReport.issues.length === 0) {
    lines.push('  🟢 No issues found');
  } else {
    for (const issue of genesReport.issues) {
      lines.push(`  ${severityIcon[issue.severity]} [${issue.check}] ${issue.message}`);
    }
  }

  const total = narrativeReport.summary.total + genesReport.summary.total;
  const critical = narrativeReport.summary.critical + genesReport.summary.critical;
  lines.push('', `## Summary: ${total} issues (${critical} critical, ${narrativeReport.summary.warning + genesReport.summary.warning} warning, ${narrativeReport.summary.info + genesReport.summary.info} info)`);

  return lines.join('\n');
}

/**
 * Main entry point
 */
async function main(opts = {}) {
  const narrativePath = opts.narrativePath || DEFAULTS.narrativePath;
  const genesPath = opts.genesPath || DEFAULTS.genesPath;

  const narrativeContent = readFileOrNull(narrativePath);
  const genesContent = readFileOrNull(genesPath);

  const narrativeReport = lintNarrative(narrativeContent, genesContent);
  const genesReport = lintGenes(genesContent);

  const report = formatReport(narrativeReport, genesReport);
  console.log(report);

  return {
    narrative: narrativeReport,
    genes: genesReport,
    totalIssues: narrativeReport.summary.total + genesReport.summary.total,
    clean: narrativeReport.summary.total + genesReport.summary.total === 0,
  };
}

module.exports = { main, lintNarrative, lintGenes, parseNarrativeEntries, loadGeneRegistry };
