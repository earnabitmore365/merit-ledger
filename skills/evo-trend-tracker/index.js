/**
 * evo-trend-tracker: Time-series analysis of evolution metrics.
 *
 * Tracks rolling success rates, innovation ratios, blast radius averages,
 * and gene diversity over time windows to identify trends and momentum shifts.
 * Distinct from evolution-scorecard (point-in-time score) — this shows HOW
 * metrics change over time using linear regression.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const DEFAULTS = {
  narrativePath: path.join(os.homedir(), '.claude/evolver/evolution/evolution_narrative.md'),
  windowSize: 5,
};

/**
 * Parse narrative entries from evolution_narrative.md
 */
function parseEntries(content) {
  if (!content) return [];
  const entries = [];
  const lines = content.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const hdr = lines[i].match(
      /^### \[(\d{4}-\d{2}-\d{2})[\sT]([\d:]+(?:\.\d+)?)\]\s+(INNOVATE|OPTIMIZE|REPAIR)\s+-\s+(success|failed)/i
    );
    if (!hdr) continue;

    const entry = {
      date: hdr[1],
      time: hdr[2],
      intent: hdr[3].toUpperCase(),
      outcome: hdr[4].toLowerCase(),
      gene: null,
      score: 0,
      scope: { files: 0, lines: 0 },
    };

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
    }

    entries.push(entry);
  }

  return entries;
}

/**
 * Compute metrics for a window of entries
 */
function windowMetrics(entries) {
  const total = entries.length;
  if (total === 0) return null;

  const successes = entries.filter(e => e.outcome === 'success').length;
  const innovates = entries.filter(e => e.intent === 'INNOVATE').length;
  const uniqueGenes = new Set(entries.filter(e => e.gene).map(e => e.gene)).size;
  const avgFiles = entries.reduce((s, e) => s + e.scope.files, 0) / total;
  const avgLines = entries.reduce((s, e) => s + e.scope.lines, 0) / total;
  const zeroChange = entries.filter(e => e.scope.files === 0 && e.scope.lines === 0).length;

  return {
    count: total,
    successRate: Math.round((successes / total) * 100),
    innovationRatio: Math.round((innovates / total) * 100),
    avgFiles: Math.round(avgFiles * 10) / 10,
    avgLines: Math.round(avgLines * 10) / 10,
    zeroChangeRate: Math.round((zeroChange / total) * 100),
    geneDiversity: uniqueGenes,
  };
}

/**
 * Simple linear regression on an array of numbers.
 * Returns { slope, intercept, r2 }
 */
function linearRegression(values) {
  const n = values.length;
  if (n < 2) return { slope: 0, intercept: values[0] || 0, r2: 0 };

  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
  for (let i = 0; i < n; i++) {
    sumX += i;
    sumY += values[i];
    sumXY += i * values[i];
    sumX2 += i * i;
  }

  const denom = n * sumX2 - sumX * sumX;
  if (denom === 0) return { slope: 0, intercept: sumY / n, r2: 0 };

  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;

  const meanY = sumY / n;
  let ssRes = 0, ssTot = 0;
  for (let i = 0; i < n; i++) {
    const predicted = intercept + slope * i;
    ssRes += (values[i] - predicted) ** 2;
    ssTot += (values[i] - meanY) ** 2;
  }
  const r2 = ssTot === 0 ? 0 : Math.round((1 - ssRes / ssTot) * 100) / 100;

  return {
    slope: Math.round(slope * 100) / 100,
    intercept: Math.round(intercept * 100) / 100,
    r2,
  };
}

/**
 * Classify trend direction based on slope magnitude and fit quality
 */
function classifyTrend(slope, r2) {
  if (Math.abs(r2) < 0.3) return 'flat';
  if (slope > 1) return 'improving';
  if (slope < -1) return 'degrading';
  return 'flat';
}

/**
 * Compute rolling window trends across all entries
 */
function computeTrends(entries, windowSize) {
  if (entries.length < windowSize) {
    return { windows: [], trends: null, overall: 'insufficient_data', summary: 'Insufficient data for trend analysis.' };
  }

  const windows = [];
  for (let i = 0; i <= entries.length - windowSize; i++) {
    const slice = entries.slice(i, i + windowSize);
    const metrics = windowMetrics(slice);
    windows.push({ startDate: slice[0].date, endDate: slice[slice.length - 1].date, ...metrics });
  }

  const successRates = windows.map(w => w.successRate);
  const innovationRatios = windows.map(w => w.innovationRatio);
  const avgLinesSeries = windows.map(w => w.avgLines);
  const zeroChangeRates = windows.map(w => w.zeroChangeRate);
  const geneDiversities = windows.map(w => w.geneDiversity);

  const srTrend = linearRegression(successRates);
  const irTrend = linearRegression(innovationRatios);
  const alTrend = linearRegression(avgLinesSeries);
  const zcTrend = linearRegression(zeroChangeRates);
  const gdTrend = linearRegression(geneDiversities);

  const trends = {
    successRate: { ...srTrend, direction: classifyTrend(srTrend.slope, srTrend.r2) },
    innovationRatio: { ...irTrend, direction: classifyTrend(irTrend.slope, irTrend.r2) },
    avgLines: { ...alTrend, direction: classifyTrend(alTrend.slope, alTrend.r2) },
    zeroChangeRate: { ...zcTrend, direction: classifyTrend(-zcTrend.slope, zcTrend.r2) },
    geneDiversity: { ...gdTrend, direction: classifyTrend(gdTrend.slope, gdTrend.r2) },
  };

  const improving = Object.values(trends).filter(t => t.direction === 'improving').length;
  const degrading = Object.values(trends).filter(t => t.direction === 'degrading').length;
  const flat = 5 - improving - degrading;
  let overall;
  if (improving > degrading) overall = 'improving';
  else if (degrading > improving) overall = 'degrading';
  else overall = 'flat';

  return {
    windows,
    trends,
    overall,
    summary: `${improving} improving, ${degrading} degrading, ${flat} flat metrics. Overall: ${overall}.`,
  };
}

/**
 * Main entry point
 * @param {Object} opts - { narrativePath, windowSize }
 * @returns {Promise<Object>} Trend analysis result
 */
async function main(opts = {}) {
  const narrativePath = opts.narrativePath || DEFAULTS.narrativePath;
  const windowSize = opts.windowSize || DEFAULTS.windowSize;

  let content;
  try {
    content = fs.readFileSync(narrativePath, 'utf8');
  } catch (err) {
    return { error: `Cannot read narrative: ${err.message}` };
  }

  const entries = parseEntries(content);
  if (entries.length === 0) {
    return { error: 'No entries found in narrative.' };
  }

  const currentMetrics = windowMetrics(entries.slice(-windowSize));
  const trendAnalysis = computeTrends(entries, windowSize);

  return {
    totalEntries: entries.length,
    windowSize,
    dateRange: { first: entries[0].date, last: entries[entries.length - 1].date },
    current: currentMetrics,
    ...trendAnalysis,
  };
}

module.exports = { main, parseEntries, windowMetrics, linearRegression, computeTrends };
