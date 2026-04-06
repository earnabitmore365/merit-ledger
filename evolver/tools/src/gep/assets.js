const { computeAssetId, SCHEMA_VERSION } = require('./contentHash');

/**
 * Summarize epigenetic marks into a compact string for prompt display.
 * e.g. "boost: +0.35 (2 marks)" or "boost: -0.15 (1 mark)"
 */
function summarizeEpigenetics(marks) {
  if (!Array.isArray(marks) || marks.length === 0) return null;
  var total = 0;
  for (var i = 0; i < marks.length; i++) {
    if (marks[i] && Number.isFinite(marks[i].boost)) total += marks[i].boost;
  }
  var sign = total >= 0 ? '+' : '';
  return sign + total.toFixed(2) + ' (' + marks.length + ' mark' + (marks.length > 1 ? 's' : '') + ')';
}

/**
 * Format asset preview for prompt inclusion.
 * Handles stringified JSON, arrays, and error cases gracefully.
 * Injects compact epigenetic summaries for Gene assets.
 */
function formatAssetPreview(preview) {
  if (!preview) return '(none)';
  var data = preview;
  if (typeof preview === 'string') {
      try {
          data = JSON.parse(preview);
          if (!Array.isArray(data) || data.length === 0) return preview;
      } catch (e) {
          return preview;
      }
  }
  // Annotate genes with epigenetic summary for prompt visibility
  if (Array.isArray(data)) {
    for (var i = 0; i < data.length; i++) {
      var item = data[i];
      if (item && item.type === 'Gene' && Array.isArray(item.epigenetic_marks) && item.epigenetic_marks.length > 0) {
        item._epi_summary = summarizeEpigenetics(item.epigenetic_marks);
      }
    }
  }
  return JSON.stringify(data, null, 2);
}

/**
 * Validate and normalize an asset object.
 * Ensures schema version and ID are present.
 */
function normalizeAsset(asset) {
  if (!asset || typeof asset !== 'object') return asset;
  if (!asset.schema_version) asset.schema_version = SCHEMA_VERSION;
  if (!asset.asset_id) {
    try { asset.asset_id = computeAssetId(asset); } catch (e) {}
  }
  return asset;
}

module.exports = { formatAssetPreview, normalizeAsset };
