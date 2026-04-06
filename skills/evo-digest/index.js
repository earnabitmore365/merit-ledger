/**
 * evo-digest: Human-readable evolution digest generator
 *
 * Reads evolution_narrative.md, MEMORY.md, and genes.json
 * to produce a concise digest report for the boss.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const DEFAULTS = {
  narrativePath: path.join(os.homedir(), '.claude/evolver/evolution/evolution_narrative.md'),
  memoryPath: path.join(os.homedir(), '.claude/evolver/MEMORY.md'),
  genesPath: path.join(os.homedir(), '.claude/evolver/assets/gep/genes.json'),
};

function readFileOrNull(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}

/**
 * Parse evolution_narrative.md into structured cycle entries
 */
function parseNarrative(content) {
  if (!content) return [];
  const entries = [];
  const lines = content.split('\n');
  let current = null;

  for (const line of lines) {
    const headerMatch = line.match(/^### \[(\d{4}-\d{2}-\d{2}[^\]]*)\]\s+(INNOVATE|OPTIMIZE|REPAIR)\s+-\s+(success|failed)/i);
    if (headerMatch) {
      if (current) entries.push(current);
      current = {
        date: headerMatch[1].trim(),
        intent: headerMatch[2].toUpperCase(),
        status: headerMatch[3].toLowerCase(),
        gene: null,
        score: null,
        scope: { files: 0, lines: 0 },
        result: '',
      };
      continue;
    }
    if (!current) continue;

    const geneMatch = line.match(/Gene:\s+(gene_\S+)/);
    if (geneMatch) current.gene = geneMatch[1];

    const scoreMatch = line.match(/Score:\s+([\d.]+)/);
    if (scoreMatch) current.score = parseFloat(scoreMatch[1]);

    const scopeMatch = line.match(/Scope:\s+(\d+)\s+files?,\s+(\d+)\s+lines?/);
    if (scopeMatch) {
      current.scope.files = parseInt(scopeMatch[1]);
      current.scope.lines = parseInt(scopeMatch[2]);
    }

    const resultMatch = line.match(/Result:\s+(.+)/);
    if (resultMatch) current.result = resultMatch[1].trim();
  }
  if (current) entries.push(current);
  return entries;
}

/**
 * Calculate aggregate metrics from parsed cycles
 */
function calcMetrics(cycles) {
  if (!cycles.length) return { total: 0, successRate: 0, innovationRatio: 0, avgScore: 0, totalFiles: 0, totalLines: 0, geneDistribution: {}, intentDistribution: {} };

  const successes = cycles.filter(c => c.status === 'success');
  const innovations = cycles.filter(c => c.intent === 'INNOVATE');
  const scores = successes.map(c => c.score).filter(Boolean);

  const geneDistribution = {};
  const intentDistribution = {};
  let totalFiles = 0;
  let totalLines = 0;

  for (const c of cycles) {
    if (c.gene) geneDistribution[c.gene] = (geneDistribution[c.gene] || 0) + 1;
    intentDistribution[c.intent] = (intentDistribution[c.intent] || 0) + 1;
    totalFiles += c.scope.files;
    totalLines += c.scope.lines;
  }

  return {
    total: cycles.length,
    successRate: cycles.length ? (successes.length / cycles.length * 100).toFixed(1) : 0,
    innovationRatio: cycles.length ? (innovations.length / cycles.length * 100).toFixed(1) : 0,
    avgScore: scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2) : 0,
    totalFiles,
    totalLines,
    geneDistribution,
    intentDistribution,
  };
}

/**
 * Detect health indicators from cycles and gene data
 */
function assessHealth(cycles, genes) {
  const indicators = [];
  const recent = cycles.slice(-5);

  // Stagnation check: same gene used 3+ times consecutively
  if (recent.length >= 3) {
    const lastGenes = recent.slice(-3).map(c => c.gene);
    if (lastGenes.every(g => g === lastGenes[0])) {
      indicators.push({ level: 'warning', msg: `基因停滞：最近3个周期都使用 ${lastGenes[0]}` });
    }
  }

  // Zero-change check
  const zeroChanges = recent.filter(c => c.scope.files === 0 && c.scope.lines === 0);
  if (zeroChanges.length >= 2) {
    indicators.push({ level: 'critical', msg: `空周期警告：最近5个周期中有 ${zeroChanges.length} 个零变更` });
  }

  // Innovation drought
  const recentInnovations = recent.filter(c => c.intent === 'INNOVATE');
  if (recent.length >= 5 && recentInnovations.length === 0) {
    indicators.push({ level: 'warning', msg: '创新干旱：最近5个周期无创新' });
  }

  // Gene diversity
  const activeGeneCount = genes ? genes.length : 0;
  if (activeGeneCount < 4) {
    indicators.push({ level: 'info', msg: `基因池较小：仅 ${activeGeneCount} 个活跃基因` });
  }

  if (!indicators.length) {
    indicators.push({ level: 'healthy', msg: '系统健康，无异常检测' });
  }

  return indicators;
}

/**
 * Generate the digest report as markdown
 */
function generateDigest(opts = {}) {
  const narrativePath = opts.narrativePath || DEFAULTS.narrativePath;
  const memoryPath = opts.memoryPath || DEFAULTS.memoryPath;
  const genesPath = opts.genesPath || DEFAULTS.genesPath;

  const narrativeContent = readFileOrNull(narrativePath);
  const genesContent = readFileOrNull(genesPath);

  const cycles = parseNarrative(narrativeContent);
  let genes = [];
  try { genes = JSON.parse(genesContent).genes || []; } catch {}

  const metrics = calcMetrics(cycles);
  const health = assessHealth(cycles, genes);

  const levelIcon = { critical: '🔴', warning: '🟡', info: '🔵', healthy: '🟢' };

  const topGenes = Object.entries(metrics.geneDistribution)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([g, count]) => `  - ${g}: ${count} 次`)
    .join('\n');

  const intentBreakdown = Object.entries(metrics.intentDistribution)
    .map(([intent, count]) => `${intent}: ${count}`)
    .join(' | ');

  const recentChanges = cycles.slice(-5)
    .reverse()
    .map(c => `  - [${c.status === 'success' ? '✅' : '❌'}] ${c.intent} | ${c.gene || '?'} | ${c.scope.files}f/${c.scope.lines}L | ${c.result.slice(0, 80)}`)
    .join('\n');

  const healthLines = health
    .map(h => `  ${levelIcon[h.level] || '⚪'} ${h.msg}`)
    .join('\n');

  const report = `# Evolution Digest
> 生成时间: ${new Date().toISOString().slice(0, 19)}
> 数据范围: ${cycles.length} 个周期

## 概览

| 指标 | 值 |
|------|-----|
| 总周期数 | ${metrics.total} |
| 成功率 | ${metrics.successRate}% |
| 创新占比 | ${metrics.innovationRatio}% |
| 平均评分 | ${metrics.avgScore} |
| 总变更 | ${metrics.totalFiles} 文件 / ${metrics.totalLines} 行 |
| 意图分布 | ${intentBreakdown} |

## 最近变更

${recentChanges}

## 基因使用排行

${topGenes}

## 健康指标

${healthLines}

## 活跃基因池

${genes.map(g => `  - ${g.id} (${g.category}) — 信号: [${(g.signals_match || []).join(', ')}]`).join('\n')}
`;

  return report;
}

/**
 * Main entry point - prints digest to stdout
 */
async function main() {
  const report = generateDigest();
  console.log(report);
  return report;
}

module.exports = { main, generateDigest, parseNarrative, calcMetrics, assessHealth };
