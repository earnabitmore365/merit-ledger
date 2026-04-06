'use strict';

const fs = require('fs');
const path = require('path');

const EVOLVER_ROOT = path.join(process.env.HOME || '/Users/allenbot', '.claude', 'evolver');
const EVENTS_PATH = path.join(EVOLVER_ROOT, 'assets', 'gep', 'events.jsonl');
const GENES_PATH = path.join(EVOLVER_ROOT, 'assets', 'gep', 'genes.json');

function loadEvents() {
  if (!fs.existsSync(EVENTS_PATH)) return [];
  return fs.readFileSync(EVENTS_PATH, 'utf8')
    .split('\n')
    .filter(l => l.trim())
    .map(l => { try { return JSON.parse(l); } catch { return null; } })
    .filter(e => e && e.type === 'EvolutionEvent');
}

function loadGenes() {
  if (!fs.existsSync(GENES_PATH)) return { active: [], retired: [] };
  const data = JSON.parse(fs.readFileSync(GENES_PATH, 'utf8'));
  if (data.active_genes && data.retired_genes) {
    return { active: data.active_genes, retired: data.retired_genes };
  }
  if (Array.isArray(data)) {
    return { active: data, retired: [] };
  }
  return { active: [], retired: [] };
}

function signalOverlap(eventSignals, querySignals) {
  const eSet = new Set(eventSignals || []);
  let overlap = 0;
  for (const s of querySignals) {
    if (eSet.has(s)) overlap++;
  }
  return querySignals.length > 0 ? overlap / querySignals.length : 0;
}

function recommend(querySignals, options) {
  const opts = options || {};
  const topN = opts.topN || 5;
  const excludeGenes = opts.excludeGenes || [];
  const intentFilter = opts.intentFilter || null;

  const events = loadEvents();
  const genesData = loadGenes();
  const retiredIds = new Set((genesData.retired || []).map(function(g) {
    return typeof g === 'string' ? g : g.id;
  }));
  const excludeSet = new Set(excludeGenes);

  // Build gene performance map from event history
  var geneStats = {};

  for (var i = 0; i < events.length; i++) {
    var evt = events[i];
    if (!evt.genes_used || !evt.outcome) continue;
    for (var j = 0; j < evt.genes_used.length; j++) {
      var geneId = evt.genes_used[j];
      if (!geneStats[geneId]) {
        geneStats[geneId] = {
          total: 0, success: 0, failed: 0,
          signals: [], blastRadii: [], scores: []
        };
      }
      var gs = geneStats[geneId];
      gs.total++;
      if (evt.outcome.status === 'success') gs.success++;
      else gs.failed++;
      if (evt.signals) gs.signals = gs.signals.concat(evt.signals);
      if (evt.blast_radius) gs.blastRadii.push(evt.blast_radius);
      if (evt.outcome.score != null) gs.scores.push(evt.outcome.score);
    }
  }

  // Score each gene for the query signals
  var recommendations = [];
  var geneIds = Object.keys(geneStats);

  for (var k = 0; k < geneIds.length; k++) {
    var id = geneIds[k];
    var stats = geneStats[id];

    if (excludeSet.has(id)) continue;

    var isRetired = retiredIds.has(id);

    // Signal affinity: fraction of query signals seen in gene history
    var uniqueSignals = [];
    var seen = {};
    for (var s = 0; s < stats.signals.length; s++) {
      if (!seen[stats.signals[s]]) {
        seen[stats.signals[s]] = true;
        uniqueSignals.push(stats.signals[s]);
      }
    }
    var affinity = signalOverlap(uniqueSignals, querySignals);

    // Success rate
    var successRate = stats.total > 0 ? stats.success / stats.total : 0;

    // Average score
    var avgScore = 0;
    if (stats.scores.length > 0) {
      var sum = 0;
      for (var m = 0; m < stats.scores.length; m++) sum += stats.scores[m];
      avgScore = sum / stats.scores.length;
    }

    // Average blast radius (files)
    var avgFiles = 0;
    if (stats.blastRadii.length > 0) {
      var fsum = 0;
      for (var n = 0; n < stats.blastRadii.length; n++) {
        fsum += (stats.blastRadii[n].files || 0);
      }
      avgFiles = fsum / stats.blastRadii.length;
    }

    // Composite: 40% affinity + 30% success rate + 20% avg score + 10% experience
    var experienceBonus = stats.total > 2 ? 0.1 : 0;
    var composite = (affinity * 0.4) + (successRate * 0.3) + (avgScore * 0.2) + experienceBonus;

    // Find active gene details
    var geneDetail = null;
    for (var p = 0; p < genesData.active.length; p++) {
      if (genesData.active[p].id === id) { geneDetail = genesData.active[p]; break; }
    }

    var warning = null;
    if (isRetired) warning = 'RETIRED - avoid using';
    else if (successRate < 0.3 && stats.total > 1) warning = 'LOW SUCCESS RATE - consider alternatives';
    else if (stats.failed > 3) warning = 'HIGH FAILURE COUNT - may be problematic';

    recommendations.push({
      gene_id: id,
      composite_score: Math.round(composite * 100) / 100,
      signal_affinity: Math.round(affinity * 100) / 100,
      success_rate: Math.round(successRate * 100) / 100,
      avg_score: Math.round(avgScore * 100) / 100,
      avg_blast_files: Math.round(avgFiles * 10) / 10,
      total_uses: stats.total,
      retired: isRetired,
      category: geneDetail ? geneDetail.category : 'unknown',
      warning: warning
    });
  }

  // Sort by composite score descending
  recommendations.sort(function(a, b) { return b.composite_score - a.composite_score; });

  // Filter by intent if specified
  var filtered = recommendations;
  if (intentFilter) {
    filtered = recommendations.filter(function(r) {
      return r.category === intentFilter || r.category === 'unknown';
    });
  }

  var topRecs = filtered.slice(0, topN);
  var warnings = recommendations.filter(function(r) {
    return (r.retired || r.warning) && !topRecs.find(function(t) { return t.gene_id === r.gene_id; });
  });

  return {
    query_signals: querySignals,
    intent_filter: intentFilter,
    total_genes_analyzed: geneIds.length,
    recommendations: topRecs,
    warnings: warnings,
    summary: topRecs.length > 0
      ? 'Top recommendation: ' + topRecs[0].gene_id + ' (score: ' + topRecs[0].composite_score + ', success: ' + topRecs[0].success_rate + ')'
      : 'No suitable genes found for these signals'
  };
}

function main() {
  var signals = process.argv.slice(2);
  var querySignals = signals.length > 0 ? signals : ['protocol_drift', 'evolution_stagnation_detected'];

  var result = recommend(querySignals);
  console.log(JSON.stringify(result, null, 2));
  return result;
}

module.exports = { recommend: recommend, main: main, loadEvents: loadEvents, loadGenes: loadGenes };

if (require.main === module) {
  main();
}
