'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const REQUIRED_FILES = ['index.js', 'SKILL.md', 'package.json'];
const FRONTMATTER_RE = /^---\n([\s\S]*?)\n---/;

/**
 * Parse YAML-like frontmatter (simple key: value pairs).
 * @param {string} content
 * @returns {{ name?: string, description?: string } | null}
 */
function parseFrontmatter(content) {
  const match = content.match(FRONTMATTER_RE);
  if (!match) return null;
  const result = {};
  for (const line of match[1].split('\n')) {
    const idx = line.indexOf(':');
    if (idx > 0) {
      const key = line.slice(0, idx).trim();
      const val = line.slice(idx + 1).trim();
      result[key] = val;
    }
  }
  return result;
}

/**
 * Validate a single skill directory.
 * @param {string} skillDir - Absolute path to the skill directory
 * @param {{ quiet: boolean }} opts
 * @returns {{ skill: string, status: 'healthy'|'broken'|'warning', checks: object, errors: string[], warnings: string[] }}
 */
function validateSkill(skillDir, { quiet }) {
  const skillName = path.basename(skillDir);
  const checks = { files: 'skip', frontmatter: 'skip', package: 'skip', exports: 'skip' };
  const errors = [];
  const warnings = [];

  // 1. Required files check
  const missing = REQUIRED_FILES.filter(f => !fs.existsSync(path.join(skillDir, f)));
  if (missing.length > 0) {
    checks.files = 'fail';
    errors.push(`Missing: ${missing.join(', ')}`);
  } else {
    checks.files = 'pass';

    // Check for empty files
    for (const f of REQUIRED_FILES) {
      const stat = fs.statSync(path.join(skillDir, f));
      if (stat.size === 0) {
        warnings.push(`Empty file: ${f}`);
      }
    }
  }

  // 2. SKILL.md frontmatter check
  if (checks.files === 'pass' || fs.existsSync(path.join(skillDir, 'SKILL.md'))) {
    try {
      const content = fs.readFileSync(path.join(skillDir, 'SKILL.md'), 'utf8');
      const fm = parseFrontmatter(content);
      if (!fm) {
        checks.frontmatter = 'fail';
        errors.push('SKILL.md missing YAML frontmatter');
      } else if (!fm.name || !fm.description) {
        checks.frontmatter = 'fail';
        const missingFields = [];
        if (!fm.name) missingFields.push('name');
        if (!fm.description) missingFields.push('description');
        errors.push(`SKILL.md frontmatter missing: ${missingFields.join(', ')}`);
      } else {
        checks.frontmatter = 'pass';
      }
    } catch (err) {
      checks.frontmatter = 'fail';
      errors.push(`SKILL.md read error: ${err.message}`);
    }
  }

  // 3. package.json validity check
  if (checks.files === 'pass' || fs.existsSync(path.join(skillDir, 'package.json'))) {
    try {
      const raw = fs.readFileSync(path.join(skillDir, 'package.json'), 'utf8');
      const pkg = JSON.parse(raw);
      if (!pkg.name) {
        checks.package = 'fail';
        errors.push('package.json missing "name" field');
      } else {
        checks.package = 'pass';
      }
    } catch (err) {
      checks.package = 'fail';
      errors.push(`package.json invalid: ${err.message}`);
    }
  }

  // 4. Export importability check
  if (checks.files === 'pass' || fs.existsSync(path.join(skillDir, 'index.js'))) {
    const indexPath = path.join(skillDir, 'index.js');
    const result = spawnSync('node', ['-e', `const m = require('${indexPath}'); console.log(Object.keys(m).join(','))`], {
      encoding: 'utf8',
      timeout: 10000,
    });
    if (result.status !== 0) {
      checks.exports = 'fail';
      const errMsg = ((result.stderr || '') + (result.stdout || '')).trim().split('\n')[0];
      errors.push(`Import failed: ${errMsg}`);
    } else {
      checks.exports = 'pass';
    }
  }

  // Determine overall status
  let status = 'healthy';
  if (errors.length > 0) {
    status = 'broken';
  } else if (warnings.length > 0) {
    status = 'warning';
  }

  if (!quiet) {
    const icon = status === 'healthy' ? '✓' : status === 'warning' ? '⚠' : '✗';
    process.stdout.write(`  ${icon} ${skillName}: ${status}`);
    if (errors.length > 0) process.stdout.write(` (${errors[0]})`);
    if (warnings.length > 0 && errors.length === 0) process.stdout.write(` (${warnings[0]})`);
    process.stdout.write('\n');
  }

  return { skill: skillName, status, checks, errors, warnings };
}

/**
 * Batch-validate all skills in a directory.
 * @param {{ skillsDir?: string, format?: 'text'|'json', quiet?: boolean }} [options]
 * @returns {Promise<{ healthy: number, broken: number, warnings: number, total: number, summary: string, results: Array }>}
 */
async function run(options = {}) {
  const {
    skillsDir = path.join(process.env.HOME || '/tmp', '.claude', 'skills'),
    format = 'text',
    quiet = false,
  } = options;

  if (!fs.existsSync(skillsDir)) {
    return { healthy: 0, broken: 0, warnings: 0, total: 0, summary: 'Skills directory not found', results: [] };
  }

  const entries = fs.readdirSync(skillsDir, { withFileTypes: true })
    .filter(e => e.isDirectory())
    .map(e => e.name)
    .sort();

  if (!quiet) {
    process.stdout.write(`\nskill-validator: scanning ${entries.length} skill(s) in ${skillsDir}\n\n`);
  }

  const results = entries.map(name => validateSkill(path.join(skillsDir, name), { quiet }));

  const healthy = results.filter(r => r.status === 'healthy').length;
  const broken = results.filter(r => r.status === 'broken').length;
  const warns = results.filter(r => r.status === 'warning').length;
  const total = results.length;
  const summary = `${healthy} healthy, ${broken} broken, ${warns} warning`;

  const report = { healthy, broken, warnings: warns, total, summary, results };

  if (!quiet) {
    const icon = broken === 0 ? '✅' : '❌';
    process.stdout.write(`\n${icon} ${summary} (${total} total)\n`);
  }

  if (format === 'json') {
    return JSON.stringify(report, null, 2);
  }

  return report;
}

/**
 * CLI entry point: node skills/skill-validator [skillsDir]
 */
async function main() {
  const args = process.argv.slice(2);
  const skillsDir = args[0] || undefined;
  const report = await run({ skillsDir });
  if (report.broken > 0) process.exit(1);
}

module.exports = { run, main };

if (require.main === module) {
  main().catch(err => {
    process.stderr.write(`skill-validator error: ${err.message}\n`);
    process.exit(1);
  });
}
