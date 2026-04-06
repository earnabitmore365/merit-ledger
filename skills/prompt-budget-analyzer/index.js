/**
 * prompt-budget-analyzer: Analyzes GEP prompt composition and tracks section size trends
 *
 * Parses gep_prompt_run_*.txt files to break down how much space each context section
 * uses, detects bloat trends across cycles, and recommends compression targets.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const EVOLUTION_DIR = path.join(os.homedir(), '.claude/evolver/evolution');
const PROMPT_PATTERN = /^gep_prompt_run_(\d+)\.txt$/;

// Known section markers in GEP prompts
const SECTION_MARKERS = [
  { key: 'protocol_header', start: /^GEP — GENOME EVOLUTION PROTOCOL/, end: /^Context \[/ },
  { key: 'signals', start: /^Context \[Signals\]/, end: /^Context \[/ },
  { key: 'env_fingerprint', start: /^Context \[Env Fingerprint\]/, end: /^Context \[/ },
  { key: 'innovation_catalyst', start: /^Context \[Innovation Catalyst\]/, end: /^Context \[/ },
  { key: 'injection_hint', start: /^Context \[Injection Hint\]/, end: /^Context \[/ },
  { key: 'gene_preview', start: /^Context \[Gene Preview\]/, end: /^Context \[/ },
  { key: 'capsule_preview', start: /^Context \[Capsule Preview\]/, end: /^Context \[/ },
  { key: 'capability_candidates', start: /^Context \[Capability Candidates\]/, end: /^Context \[/ },
  { key: 'hub_match', start: /^Context \[Hub Matched Solution\]/, end: /^Context \[/ },
  { key: 'external_candidates', start: /^Context \[External Candidates\]/, end: /^Context \[/ },
  { key: 'evolution_narrative', start: /^Context \[Evolution Narrative\]/, end: /^Context \[/ },
  { key: 'execution_context', start: /^Context \[Execution\]/, end: /^$END$/ },
];

const SECTION_LABELS = {
  preamble: 'Preamble (pre-GEP)',
  protocol_header: 'Protocol Header',
  signals: 'Signals',
  env_fingerprint: 'Env Fingerprint',
  innovation_catalyst: 'Innovation Catalyst',
  injection_hint: 'Injection Hint',
  gene_preview: 'Gene Preview',
  capsule_preview: 'Capsule Preview',
  capability_candidates: 'Capability Candidates',
  hub_match: 'Hub Matched Solution',
  external_candidates: 'External Candidates',
  evolution_narrative: 'Evolution Narrative',
  execution_context: 'Execution Context',
  tail: 'Post-solidify / Tail',
};

/**
 * List available GEP prompt files sorted by timestamp
 */
function listPromptFiles(dir) {
  try {
    const files = fs.readdirSync(dir);
    return files
      .filter(f => PROMPT_PATTERN.test(f))
      .map(f => {
        const ts = parseInt(f.match(PROMPT_PATTERN)[1], 10);
        return { file: f, timestamp: ts, path: path.join(dir, f) };
      })
      .sort((a, b) => a.timestamp - b.timestamp);
  } catch { return []; }
}

/**
 * Parse a single prompt file into sections with line/byte counts
 */
function parsePromptSections(filePath) {
  let content;
  try { content = fs.readFileSync(filePath, 'utf8'); } catch { return null; }

  const lines = content.split('\n');
  const totalLines = lines.length;
  const totalBytes = Buffer.byteLength(content, 'utf8');

  const sections = {};
  let currentSection = 'preamble';
  let sectionStart = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check if this line starts a new known section
    for (const marker of SECTION_MARKERS) {
      if (marker.start.test(line)) {
        // Close previous section
        const sectionLines = lines.slice(sectionStart, i);
        sections[currentSection] = {
          lines: sectionLines.length,
          bytes: Buffer.byteLength(sectionLines.join('\n'), 'utf8'),
        };
        currentSection = marker.key;
        sectionStart = i;
        break;
      }
    }
  }

  // Close final section
  const sectionLines = lines.slice(sectionStart);
  sections[currentSection] = {
    lines: sectionLines.length,
    bytes: Buffer.byteLength(sectionLines.join('\n'), 'utf8'),
  };

  // Check for post-solidify tail (after execution_context)
  const solidifyIdx = lines.findIndex(l => /MANDATORY POST-SOLIDIFY STEP/.test(l));
  if (solidifyIdx > -1 && sections.execution_context) {
    const execEnd = sectionStart; // execution_context start
    const execLines = solidifyIdx - execEnd;
    const tailLines = lines.length - solidifyIdx;
    if (execLines > 0 && tailLines > 0) {
      sections.execution_context.lines = execLines;
      sections.execution_context.bytes = Buffer.byteLength(
        lines.slice(execEnd, solidifyIdx).join('\n'), 'utf8'
      );
      sections.tail = {
        lines: tailLines,
        bytes: Buffer.byteLength(lines.slice(solidifyIdx).join('\n'), 'utf8'),
      };
    }
  }

  return { totalLines, totalBytes, sections };
}

/**
 * Calculate trends across multiple prompt analyses
 */
function calcTrends(analyses) {
  if (analyses.length < 2) return null;

  const first = analyses[0];
  const last = analyses[analyses.length - 1];

  const trends = {};
  const allKeys = new Set([
    ...Object.keys(first.sections),
    ...Object.keys(last.sections),
  ]);

  for (const key of allKeys) {
    const firstLines = first.sections[key]?.lines || 0;
    const lastLines = last.sections[key]?.lines || 0;
    const delta = lastLines - firstLines;
    const pct = firstLines > 0 ? ((delta / firstLines) * 100).toFixed(1) : (lastLines > 0 ? '+∞' : '0');
    trends[key] = { firstLines, lastLines, delta, pct };
  }

  return {
    totalDelta: last.totalLines - first.totalLines,
    totalPct: ((last.totalLines - first.totalLines) / first.totalLines * 100).toFixed(1),
    sections: trends,
  };
}

/**
 * Identify top bloat sources (sections with largest absolute growth)
 */
function identifyBloatSources(trends) {
  if (!trends) return [];
  return Object.entries(trends.sections)
    .filter(([, v]) => v.delta > 0)
    .sort((a, b) => b[1].delta - a[1].delta)
    .slice(0, 5)
    .map(([key, v]) => ({
      section: SECTION_LABELS[key] || key,
      growth: `+${v.delta} lines (+${v.pct}%)`,
      currentLines: v.lastLines,
    }));
}

/**
 * Generate a formatted budget report
 */
function generateReport(analyses, trends) {
  const latest = analyses[analyses.length - 1];
  const lines = [];

  lines.push('# GEP Prompt Budget Analysis');
  lines.push(`\nAnalyzed: ${analyses.length} prompt file(s)`);
  lines.push(`Latest prompt: ${latest.totalLines} lines / ${(latest.totalBytes / 1024).toFixed(1)} KB`);
  lines.push('');

  // Section breakdown table
  lines.push('## Section Breakdown (Latest)');
  lines.push('');
  lines.push('| Section | Lines | Bytes | % of Total |');
  lines.push('|---------|------:|------:|-----------:|');

  const sortedSections = Object.entries(latest.sections)
    .sort((a, b) => b[1].lines - a[1].lines);

  for (const [key, val] of sortedSections) {
    const label = SECTION_LABELS[key] || key;
    const pct = ((val.lines / latest.totalLines) * 100).toFixed(1);
    lines.push(`| ${label} | ${val.lines} | ${(val.bytes / 1024).toFixed(1)} KB | ${pct}% |`);
  }

  // Trends
  if (trends) {
    lines.push('');
    lines.push('## Growth Trends');
    lines.push(`\nTotal prompt size: ${analyses[0].totalLines} → ${latest.totalLines} lines (${trends.totalPct}%)`);

    const bloat = identifyBloatSources(trends);
    if (bloat.length > 0) {
      lines.push('');
      lines.push('### Top Bloat Sources');
      for (const b of bloat) {
        lines.push(`- **${b.section}**: ${b.growth} (now ${b.currentLines} lines)`);
      }
    }

    const shrunk = Object.entries(trends.sections)
      .filter(([, v]) => v.delta < 0)
      .sort((a, b) => a[1].delta - b[1].delta);
    if (shrunk.length > 0) {
      lines.push('');
      lines.push('### Sections That Shrunk');
      for (const [key, v] of shrunk) {
        lines.push(`- **${SECTION_LABELS[key] || key}**: ${v.delta} lines (${v.pct}%)`);
      }
    }
  }

  // Recommendations
  lines.push('');
  lines.push('## Compression Recommendations');

  const bigSections = sortedSections
    .filter(([, val]) => (val.lines / latest.totalLines) > 0.15)
    .map(([key]) => key);

  if (bigSections.length > 0) {
    for (const key of bigSections) {
      const label = SECTION_LABELS[key] || key;
      const val = latest.sections[key];
      const pct = ((val.lines / latest.totalLines) * 100).toFixed(0);
      lines.push(`- **${label}** uses ${pct}% of prompt budget (${val.lines} lines) — consider consolidation`);
    }
  } else {
    lines.push('- No single section dominates >15% of the budget. Prompt is well-balanced.');
  }

  return lines.join('\n');
}

/**
 * Main entry point
 */
async function main(opts = {}) {
  const dir = opts.dir || EVOLUTION_DIR;
  const limit = opts.limit || 10; // analyze last N prompts

  const promptFiles = listPromptFiles(dir);
  if (promptFiles.length === 0) {
    console.log('No GEP prompt files found in', dir);
    return null;
  }

  // Take last N files
  const selected = promptFiles.slice(-limit);
  const analyses = [];

  for (const pf of selected) {
    const result = parsePromptSections(pf.path);
    if (result && result.totalLines > 10) { // skip tiny/empty files
      analyses.push({
        ...result,
        timestamp: pf.timestamp,
        file: pf.file,
      });
    }
  }

  if (analyses.length === 0) {
    console.log('No valid prompt files to analyze.');
    return null;
  }

  const trends = calcTrends(analyses);
  const report = generateReport(analyses, trends);
  console.log(report);

  return {
    promptCount: analyses.length,
    latest: analyses[analyses.length - 1],
    trends,
    bloatSources: trends ? identifyBloatSources(trends) : [],
  };
}

module.exports = { main, listPromptFiles, parsePromptSections, calcTrends, identifyBloatSources, generateReport };

if (require.main === module) {
  main().catch(err => { console.error(err); process.exit(1); });
}
