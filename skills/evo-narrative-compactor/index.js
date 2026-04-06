/**
 * evo-narrative-compactor: Automates evolution narrative compression
 *
 * Identifies groups of 3+ adjacent same-gene entries and consolidates
 * them into CONSOLIDATED blocks, reducing narrative size and eliminating
 * the need for manual optimize cycles spent on compression.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const DEFAULTS = {
  narrativePath: path.join(os.homedir(), '.claude/evolver/evolution/evolution_narrative.md'),
  minGroupSize: 3,
};

function readFileOrNull(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}

/**
 * Parse narrative into structured blocks (entries, archives, text)
 */
function parseBlocks(content) {
  if (!content) return [];
  const lines = content.split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Match entry header: ### [date] INTENT - status
    const headerMatch = line.match(
      /^### \[(\d{4}-\d{2}-\d{2}[\sT][\d:.]+)\]\s+(INNOVATE|OPTIMIZE|REPAIR)\s+-\s+(success|failed)/i
    );

    if (headerMatch) {
      const entry = {
        type: 'entry',
        startLine: i,
        lines: [line],
        dateStr: headerMatch[1].trim(),
        date: new Date(headerMatch[1].trim().replace(' ', 'T')),
        intent: headerMatch[2].toUpperCase(),
        status: headerMatch[3].toLowerCase(),
        gene: null,
        score: null,
        scope: { files: 0, lines: 0 },
        signals: [],
        result: '',
      };

      // Consume subsequent detail lines (- Gene:, - Signals:, - Result:)
      let j = i + 1;
      while (j < lines.length && !lines[j].startsWith('### ') && !lines[j].startsWith('> ') && lines[j] !== '') {
        const l = lines[j];
        entry.lines.push(l);

        const geneMatch = l.match(/Gene:\s+(gene_\S+)/);
        if (geneMatch) entry.gene = geneMatch[1];

        const scoreMatch = l.match(/Score:\s+([\d.]+)/);
        if (scoreMatch) entry.score = parseFloat(scoreMatch[1]);

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

        j++;
      }

      entry.endLine = j - 1;
      blocks.push(entry);
      i = j;
      continue;
    }

    // Archive/consolidated blocks (> **ARCHIVED** or > **CONSOLIDATED**)
    if (line.match(/^>\s+\*\*(ARCHIVED|CONSOLIDATED)\*\*/)) {
      const archiveBlock = { type: 'archive', startLine: i, lines: [line] };
      let j = i + 1;
      while (j < lines.length && lines[j].startsWith('>')) {
        archiveBlock.lines.push(lines[j]);
        j++;
      }
      archiveBlock.endLine = j - 1;
      blocks.push(archiveBlock);
      i = j;
      continue;
    }

    // Plain text (headers, blank lines, notes)
    blocks.push({ type: 'text', startLine: i, endLine: i, lines: [line] });
    i++;
  }

  return blocks;
}

/**
 * Find groups of adjacent same-gene entries that can be consolidated
 */
function findCompressibleGroups(blocks, minGroupSize) {
  const groups = [];
  let currentGroup = [];

  for (const block of blocks) {
    if (block.type !== 'entry') {
      // Flush current group if large enough
      if (currentGroup.length >= minGroupSize) {
        groups.push([...currentGroup]);
      }
      currentGroup = [];
      continue;
    }

    if (currentGroup.length === 0) {
      currentGroup.push(block);
    } else if (currentGroup[0].gene === block.gene) {
      currentGroup.push(block);
    } else {
      if (currentGroup.length >= minGroupSize) {
        groups.push([...currentGroup]);
      }
      currentGroup = [block];
    }
  }

  // Don't forget the last group
  if (currentGroup.length >= minGroupSize) {
    groups.push([...currentGroup]);
  }

  return groups;
}

/**
 * Generate a CONSOLIDATED block for a group of entries
 */
function generateConsolidatedBlock(group) {
  const gene = group[0].gene || 'unknown';
  const firstDate = group[0].dateStr.split(/[\sT]/)[0];
  const lastDate = group[group.length - 1].dateStr.split(/[\sT]/)[0];
  const dateRange = firstDate === lastDate ? firstDate : `${firstDate} to ${lastDate}`;

  const successCount = group.filter(e => e.status === 'success').length;
  const failedCount = group.filter(e => e.status === 'failed').length;

  const totalFiles = group.reduce((sum, e) => sum + e.scope.files, 0);
  const totalLines = group.reduce((sum, e) => sum + e.scope.lines, 0);

  // Collect unique intents
  const intents = [...new Set(group.map(e => e.intent))];

  // Summarize results for successes
  const successResults = group
    .filter(e => e.status === 'success' && e.result)
    .map(e => e.result);

  // Build summary text
  let summary = `> **CONSOLIDATED**: ${group.length} ${gene} cycles (${dateRange}):`;
  if (successCount > 0 && failedCount > 0) {
    summary += ` ${successCount} success + ${failedCount} failed`;
  } else if (successCount > 0) {
    summary += ` ${successCount} success`;
  } else {
    summary += ` ${failedCount} failed`;
  }
  summary += ` (total ${totalFiles} files/${totalLines} lines).`;

  // Add intent mismatch note if applicable
  if (intents.length > 1) {
    summary += ` Note: mixed intents (${intents.join(', ')}).`;
  }

  // Add brief result summary if there are successes
  if (successResults.length > 0 && successResults.length <= 2) {
    summary += ` Results: ${successResults.join('; ')}.`;
  } else if (successResults.length > 2) {
    summary += ` Results: ${successResults[0]}; and ${successResults.length - 1} more.`;
  }

  return summary;
}

/**
 * Apply compression: replace groups with CONSOLIDATED blocks
 */
function applyCompression(content, groups) {
  const lines = content.split('\n');
  
  // Build a set of line ranges to remove (sorted in reverse order to preserve indices)
  const replacements = [];
  for (const group of groups) {
    const startLine = group[0].startLine;
    const endLine = group[group.length - 1].endLine;
    const consolidated = generateConsolidatedBlock(group);
    replacements.push({ startLine, endLine, consolidated });
  }

  // Apply replacements in reverse order to preserve line numbers
  replacements.sort((a, b) => b.startLine - a.startLine);

  for (const rep of replacements) {
    // Replace the range with the consolidated block + blank line
    lines.splice(rep.startLine, rep.endLine - rep.startLine + 1, rep.consolidated, '');
  }

  return lines.join('\n');
}

/**
 * Main entry point
 */
async function main(opts = {}) {
  const narrativePath = opts.narrativePath || DEFAULTS.narrativePath;
  const minGroupSize = opts.minGroupSize || DEFAULTS.minGroupSize;
  const apply = opts.apply || false;

  const content = readFileOrNull(narrativePath);
  if (!content) {
    console.log('No narrative file found at:', narrativePath);
    return { error: 'file_not_found', narrativePath };
  }

  const blocks = parseBlocks(content);
  const entryCount = blocks.filter(b => b.type === 'entry').length;
  const groups = findCompressibleGroups(blocks, minGroupSize);

  const beforeLines = content.split('\n').length;

  if (groups.length === 0) {
    console.log(`No compressible groups found (min group size: ${minGroupSize}, entries: ${entryCount})`);
    return {
      dryRun: !apply,
      groups: [],
      entryCount,
      beforeLines,
      afterLines: beforeLines,
      saved: 0,
    };
  }

  // Report groups
  const groupSummaries = groups.map(g => ({
    gene: g[0].gene,
    count: g.length,
    dateRange: `${g[0].dateStr} to ${g[g.length - 1].dateStr}`,
    successes: g.filter(e => e.status === 'success').length,
    failures: g.filter(e => e.status === 'failed').length,
    totalFiles: g.reduce((s, e) => s + e.scope.files, 0),
    totalLines: g.reduce((s, e) => s + e.scope.lines, 0),
    consolidated: generateConsolidatedBlock(g),
  }));

  console.log(`Found ${groups.length} compressible group(s):`);
  for (const gs of groupSummaries) {
    console.log(`  - ${gs.gene}: ${gs.count} entries (${gs.dateRange}), ${gs.successes}s/${gs.failures}f`);
  }

  if (apply) {
    const compressed = applyCompression(content, groups);
    const afterLines = compressed.split('\n').length;
    fs.writeFileSync(narrativePath, compressed, 'utf8');
    console.log(`Applied: ${beforeLines} -> ${afterLines} lines (saved ${beforeLines - afterLines})`);

    return {
      dryRun: false,
      groups: groupSummaries,
      entryCount,
      beforeLines,
      afterLines,
      saved: beforeLines - afterLines,
    };
  }

  // Dry run - calculate what would happen
  const compressed = applyCompression(content, groups);
  const afterLines = compressed.split('\n').length;
  console.log(`Dry run: would compress ${beforeLines} -> ${afterLines} lines (save ${beforeLines - afterLines})`);

  return {
    dryRun: true,
    groups: groupSummaries,
    entryCount,
    beforeLines,
    afterLines,
    saved: beforeLines - afterLines,
  };
}

module.exports = { main, parseBlocks, findCompressibleGroups, generateConsolidatedBlock, applyCompression };
