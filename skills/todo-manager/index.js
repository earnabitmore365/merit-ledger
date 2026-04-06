'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const TAG_PRIORITY = { FIXME: 0, HACK: 1, XXX: 2, TODO: 3, NOTE: 4 };
const TAG_PATTERN = /\b(TODO|FIXME|HACK|XXX|NOTE)\b[:\s]*(.+)/i;

const DEFAULTS = {
  rootDir: path.join(os.homedir(), '.claude'),
  extensions: ['.js', '.ts', '.mjs', '.cjs', '.py', '.sh', '.md'],
  ignorePatterns: ['node_modules', '.git', 'dist', 'build', '.cache'],
  maxDepth: 8,
  tags: ['TODO', 'FIXME', 'HACK', 'XXX', 'NOTE'],
};

/**
 * Recursively collect source files
 */
function collectFiles(dir, extensions, ignore, depth, maxDepth) {
  if (depth > maxDepth) return [];
  let results = [];
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return results;
  }
  for (const entry of entries) {
    const name = entry.name;
    if (ignore.some(p => name === p || name.startsWith('.'))) continue;
    const fullPath = path.join(dir, name);
    if (entry.isDirectory()) {
      results = results.concat(collectFiles(fullPath, extensions, ignore, depth + 1, maxDepth));
    } else if (entry.isFile()) {
      const ext = path.extname(name).toLowerCase();
      if (extensions.length === 0 || extensions.includes(ext)) {
        results.push(fullPath);
      }
    }
  }
  return results;
}

/**
 * Extract TODO-style comments from a single file
 * Returns array of { tag, text, file, line, priority }
 */
function extractTodos(filePath, tags) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch {
    return [];
  }

  const lines = content.split('\n');
  const todos = [];
  const tagSet = new Set(tags.map(t => t.toUpperCase()));

  for (let i = 0; i < lines.length; i++) {
    const match = lines[i].match(TAG_PATTERN);
    if (!match) continue;
    const tag = match[1].toUpperCase();
    if (!tagSet.has(tag)) continue;
    const text = match[2].trim();
    if (text.length === 0) continue;
    todos.push({
      tag,
      text,
      file: filePath,
      line: i + 1,
      priority: TAG_PRIORITY[tag] != null ? TAG_PRIORITY[tag] : 99,
    });
  }
  return todos;
}

/**
 * Group todos by a key function
 */
function groupBy(items, keyFn) {
  const groups = {};
  for (const item of items) {
    const key = keyFn(item);
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }
  return groups;
}

/**
 * Main entry: scan directory, extract TODOs, return structured report
 */
async function main(opts = {}) {
  const rootDir = opts.rootDir || DEFAULTS.rootDir;
  const extensions = opts.extensions || DEFAULTS.extensions;
  const ignore = opts.ignorePatterns || DEFAULTS.ignorePatterns;
  const maxDepth = opts.maxDepth || DEFAULTS.maxDepth;
  const tags = opts.tags || DEFAULTS.tags;

  const files = collectFiles(rootDir, extensions, ignore, 0, maxDepth);
  let allTodos = [];

  for (const f of files) {
    const todos = extractTodos(f, tags);
    allTodos = allTodos.concat(todos);
  }

  // Sort by priority (FIXME first), then by file path
  allTodos.sort((a, b) => a.priority - b.priority || a.file.localeCompare(b.file) || a.line - b.line);

  // Build summary
  const byTag = groupBy(allTodos, t => t.tag);
  const tagSummary = {};
  for (const tag of Object.keys(TAG_PRIORITY)) {
    tagSummary[tag] = byTag[tag] ? byTag[tag].length : 0;
  }

  const byFile = groupBy(allTodos, t => path.relative(rootDir, t.file));
  const hotspots = Object.entries(byFile)
    .map(([file, items]) => ({ file, count: items.length }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  const report = {
    rootDir,
    filesScanned: files.length,
    totalTodos: allTodos.length,
    tagSummary,
    hotspots,
    items: allTodos.map(t => ({
      tag: t.tag,
      text: t.text,
      file: path.relative(rootDir, t.file),
      line: t.line,
    })),
  };

  if (!opts.quiet) {
    console.log('\n=== TODO Manager Report ===');
    console.log(`Root: ${rootDir}`);
    console.log(`Files scanned: ${report.filesScanned}`);
    console.log(`Total TODOs: ${report.totalTodos}`);
    console.log('\nBy tag:');
    for (const [tag, count] of Object.entries(tagSummary)) {
      if (count > 0) console.log(`  ${tag}: ${count}`);
    }
    if (hotspots.length > 0) {
      console.log('\nHotspots (most TODOs):');
      for (const h of hotspots) {
        console.log(`  ${h.count}  ${h.file}`);
      }
    }
    if (allTodos.length > 0) {
      console.log('\nTop items (by priority):');
      const top = allTodos.slice(0, 15);
      for (const t of top) {
        const rel = path.relative(rootDir, t.file);
        console.log(`  [${t.tag}] ${rel}:${t.line} — ${t.text}`);
      }
      if (allTodos.length > 15) {
        console.log(`  ... and ${allTodos.length - 15} more`);
      }
    }
  }

  return report;
}

module.exports = { main, collectFiles, extractTodos, groupBy };
