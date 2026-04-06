'use strict';

const fs = require('fs');
const path = require('path');
const { getNarrativePath, getEvolutionDir, getRepoRoot, getMemoryDir } = require('./paths');

const MAX_NARRATIVE_ENTRIES = 30;
const MAX_NARRATIVE_SIZE = 12000;

function ensureDir(dir) {
  try { if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true }); } catch (_) {}
}

function recordNarrative({ gene, signals, mutation, outcome, blast, capsule }) {
  const narrativePath = getNarrativePath();
  ensureDir(path.dirname(narrativePath));

  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const geneId = gene && gene.id ? gene.id : '(auto)';
  const category = (mutation && mutation.category) || (gene && gene.category) || 'unknown';
  const status = outcome && outcome.status ? outcome.status : 'unknown';
  const score = outcome && typeof outcome.score === 'number' ? outcome.score.toFixed(2) : '?';
  const signalsSummary = Array.isArray(signals) ? signals.slice(0, 4).join(', ') : '(none)';
  const filesChanged = blast ? blast.files : 0;
  const linesChanged = blast ? blast.lines : 0;
  const rationale = mutation && mutation.rationale
    ? String(mutation.rationale).slice(0, 200) : '';
  // Strategy block removed: it duplicates Gene Preview in the prompt and adds ~3 lines
  // of noise per entry × 8 entries = ~24 lines wasted in loadNarrativeSummary output.
  const capsuleSummary = capsule && capsule.summary ? String(capsule.summary).slice(0, 200) : '';

  const entry = [
    `### [${ts}] ${category.toUpperCase()} - ${status}`,
    `- Gene: ${geneId} | Score: ${score} | Scope: ${filesChanged} files, ${linesChanged} lines`,
    `- Signals: [${signalsSummary}]`,
    rationale ? `- Why: ${rationale}` : null,
    capsuleSummary ? `- Result: ${capsuleSummary}` : null,
    '',
  ].filter(line => line !== null).join('\n');

  let existing = '';
  try {
    if (fs.existsSync(narrativePath)) {
      existing = fs.readFileSync(narrativePath, 'utf8');
    }
  } catch (_) {}

  if (!existing.trim()) {
    existing = '# Evolution Narrative\n\nA chronological record of evolution decisions and outcomes.\n\n';
  }

  const combined = existing + entry;
  const trimmed = trimNarrative(combined);

  const tmp = narrativePath + '.tmp';
  fs.writeFileSync(tmp, trimmed, 'utf8');
  fs.renameSync(tmp, narrativePath);
}

function trimNarrative(content) {
  if (content.length <= MAX_NARRATIVE_SIZE) return content;

  const headerEnd = content.indexOf('###');
  if (headerEnd < 0) return content.slice(-MAX_NARRATIVE_SIZE);

  const header = content.slice(0, headerEnd);
  const entries = content.slice(headerEnd).split(/(?=^### \[)/m);

  while (entries.length > MAX_NARRATIVE_ENTRIES) {
    entries.shift();
  }

  let result = header + entries.join('');
  if (result.length > MAX_NARRATIVE_SIZE) {
    const keep = Math.max(1, entries.length - 5);
    result = header + entries.slice(-keep).join('');
  }

  return result;
}

function loadNarrativeSummary(maxChars) {
  const limit = Number.isFinite(maxChars) ? maxChars : 4000;
  const narrativePath = getNarrativePath();
  try {
    if (!fs.existsSync(narrativePath)) return '';
    const content = fs.readFileSync(narrativePath, 'utf8');
    if (!content.trim()) return '';

    const headerEnd = content.indexOf('###');
    if (headerEnd < 0) return '';

    const entries = content.slice(headerEnd).split(/(?=^### \[)/m);
    const recent = entries.slice(-8);
    let summary = recent.join('');
    if (summary.length > limit) {
      summary = summary.slice(-limit);
      const firstEntry = summary.indexOf('### [');
      if (firstEntry > 0) summary = summary.slice(firstEntry);
    }
    return summary.trim();
  } catch (_) {
    return '';
  }
}

/**
 * Append a row to MEMORY.md's evolution history table after a successful solidify.
 * Enforces the "每个成功的周期在此追加，不覆盖历史" rule programmatically.
 * Non-fatal: failures are silently caught to avoid breaking solidify.
 */
function appendMemoryHistory({ intent, signals, geneId, outcome, blast, capsuleSummary }) {
  try {
    // Get cycle number from evolution_state.json
    const stateFile = path.join(getEvolutionDir(), 'evolution_state.json');
    let cycleNum = '????';
    try {
      if (fs.existsSync(stateFile)) {
        const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
        cycleNum = String(state.cycleCount || 0).padStart(4, '0');
      }
    } catch (_) {}

    // Find MEMORY.md (try repo root first, then memory dir)
    const candidates = [
      path.join(getRepoRoot(), 'MEMORY.md'),
      path.join(getMemoryDir(), 'MEMORY.md'),
    ];
    const memoryFile = candidates.find(f => fs.existsSync(f));
    if (!memoryFile) return;

    const content = fs.readFileSync(memoryFile, 'utf8');
    const lines = content.split('\n');

    // Find the last row of the 进化历史 table
    let lastTableRow = -1;
    let inHistory = false;
    for (let i = 0; i < lines.length; i++) {
      if (/^##\s+进化历史/.test(lines[i])) { inHistory = true; continue; }
      if (inHistory && /^##\s/.test(lines[i])) break;
      if (inHistory && lines[i].startsWith('|')) lastTableRow = i;
    }
    if (lastTableRow < 0) return;

    // Prevent duplicate: skip if this cycle number already exists in the table
    const cycleTag = '#' + cycleNum;
    if (lines.some(l => l.startsWith('|') && l.includes(cycleTag))) return;

    // Build the new row
    const date = new Date().toISOString().slice(0, 10);
    const status = outcome && outcome.status === 'success' ? '✅' : '❌';
    const signalHint = Array.isArray(signals) ? signals.slice(0, 2).join(', ') : '';
    const intentCol = (intent || 'unknown') + ' (' + (signalHint || 'auto') + ')';
    const desc = capsuleSummary ? String(capsuleSummary).slice(0, 80) : (geneId || 'auto');
    const scope = blast ? blast.files + ' 文件 ' + blast.lines + ' 行变更' : '';
    const resultCol = status + ' ' + desc + (scope ? '，' + scope : '');
    const row = '| ' + cycleTag + ' | ' + date + ' | ' + intentCol + ' | ' + resultCol + ' |';

    // Append (never overwrite)
    lines.splice(lastTableRow + 1, 0, row);

    // Atomic write
    const tmp = memoryFile + '.tmp';
    fs.writeFileSync(tmp, lines.join('\n'), 'utf8');
    fs.renameSync(tmp, memoryFile);
  } catch (_) {
    // Non-fatal: do not break solidify
  }
}

module.exports = { recordNarrative, loadNarrativeSummary, trimNarrative, appendMemoryHistory };
