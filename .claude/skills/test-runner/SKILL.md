---
name: test-runner
description: Auto-execute test suites and validation scripts, reporting structured pass/fail results. Use when running node validate-modules, pytest, shell scripts, or any command-based test suite. Returns per-test pass/fail with summary stats. Triggers: "run tests", "validate modules", "check if tests pass", "run validation", "test the code", "auto-execute tests".
---

# test-runner

Executes a set of validation scripts or test commands and produces a structured pass/fail report.

## Usage

```js
const { run } = require('./skills/test-runner');

// Run default evolver validation
const report = await run();

// Run custom scripts
const report2 = await run({
  scripts: [
    'node scripts/validate-modules.js ./src/evolve ./src/gep/solidify',
    'node scripts/validate-modules.js ./src/gep/selector ./src/gep/memoryGraph',
  ],
  cwd: '/path/to/project',
  format: 'text', // 'text' | 'json'
});

console.log(report.summary);  // "3 passed, 0 failed"
console.log(report.passed);   // 3
console.log(report.failed);   // 0
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `scripts` | `string[]` | evolver defaults | Commands to run |
| `cwd` | `string` | `process.cwd()` | Working directory |
| `format` | `'text'\|'json'` | `'text'` | Output format |
| `timeout` | `number` | `30000` | Per-script timeout (ms) |
| `quiet` | `boolean` | `false` | Suppress stdout per script |

## Return Value

```json
{
  "passed": 2,
  "failed": 1,
  "total": 3,
  "summary": "2 passed, 1 failed",
  "results": [
    { "script": "node validate.js", "status": "pass", "duration": 120, "output": "OK" },
    { "script": "node broken.js", "status": "fail", "exitCode": 1, "output": "Error: ..." }
  ]
}
```
