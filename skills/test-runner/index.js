'use strict';

const { execSync, spawnSync } = require('child_process');
const path = require('path');

const DEFAULT_SCRIPTS = [
  'node scripts/validate-modules.js ./src/evolve ./src/gep/solidify',
  'node scripts/validate-modules.js ./src/gep/selector ./src/gep/memoryGraph',
];

/**
 * Run a single script and return a result object.
 * @param {string} script
 * @param {{ cwd: string, timeout: number, quiet: boolean }} opts
 * @returns {{ script: string, status: 'pass'|'fail', exitCode: number, duration: number, output: string }}
 */
function runScript(script, { cwd, timeout, quiet }) {
  const start = Date.now();
  let output = '';
  let exitCode = 0;

  try {
    const result = spawnSync(script, {
      shell: true,
      cwd,
      timeout,
      encoding: 'utf8',
      maxBuffer: 1024 * 1024,
    });

    exitCode = result.status !== null ? result.status : (result.error ? 1 : 0);
    output = ((result.stdout || '') + (result.stderr || '')).trim();

    if (result.error) {
      exitCode = 1;
      output = result.error.message;
    }
  } catch (err) {
    exitCode = 1;
    output = err.message;
  }

  const duration = Date.now() - start;
  const status = exitCode === 0 ? 'pass' : 'fail';

  if (!quiet) {
    const icon = status === 'pass' ? '✓' : '✗';
    process.stdout.write(`  ${icon} ${script} (${duration}ms)\n`);
    if (status === 'fail' && output) {
      process.stdout.write(`    ${output.split('\n')[0]}\n`);
    }
  }

  return { script, status, exitCode, duration, output };
}

/**
 * Run a set of validation scripts and return structured results.
 * @param {{ scripts?: string[], cwd?: string, format?: 'text'|'json', timeout?: number, quiet?: boolean }} [options]
 * @returns {Promise<{ passed: number, failed: number, total: number, summary: string, results: Array }>}
 */
async function run(options = {}) {
  const {
    scripts = DEFAULT_SCRIPTS,
    cwd = process.cwd(),
    format = 'text',
    timeout = 30000,
    quiet = false,
  } = options;

  if (!quiet) {
    process.stdout.write(`\ntest-runner: executing ${scripts.length} script(s)\n`);
  }

  const results = scripts.map(script => runScript(script, { cwd, timeout, quiet }));

  const passed = results.filter(r => r.status === 'pass').length;
  const failed = results.filter(r => r.status === 'fail').length;
  const total = results.length;
  const summary = `${passed} passed, ${failed} failed`;

  const report = { passed, failed, total, summary, results };

  if (!quiet) {
    const icon = failed === 0 ? '✅' : '❌';
    process.stdout.write(`\n${icon} ${summary}\n`);
  }

  if (format === 'json') {
    return JSON.stringify(report, null, 2);
  }

  return report;
}

/**
 * CLI entry point: node skills/test-runner [script1] [script2] ...
 */
async function main() {
  const args = process.argv.slice(2);
  const scripts = args.length > 0 ? args : DEFAULT_SCRIPTS;
  const report = await run({ scripts });
  if (report.failed > 0) process.exit(1);
}

module.exports = { run, main };

if (require.main === module) {
  main().catch(err => {
    process.stderr.write(`test-runner error: ${err.message}\n`);
    process.exit(1);
  });
}
