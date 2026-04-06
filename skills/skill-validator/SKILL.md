---
name: skill-validator
description: Batch-validate all installed skills for structural integrity — checks required files (index.js, SKILL.md, package.json), YAML frontmatter, export importability, and common issues. Use when auditing skill health, after bulk skill creation, or when diagnosing broken skill installations.
---

# skill-validator

Scans a skills directory and validates each skill for structural correctness.

## Checks Performed

1. **Required files**: index.js, SKILL.md, package.json must exist
2. **SKILL.md frontmatter**: Must have YAML frontmatter with `name` and `description`
3. **package.json validity**: Must be valid JSON with `name` field
4. **Export importability**: `require('./index.js')` must not throw
5. **Empty file detection**: Flags zero-byte files as warnings

## Usage

```js
const { run } = require('./skills/skill-validator');

// Validate default skills directory
const report = await run();

// Validate custom directory
const report2 = await run({ skillsDir: '/path/to/skills' });

console.log(report.summary);   // "25 healthy, 2 broken, 1 warning"
console.log(report.healthy);   // 25
console.log(report.broken);    // 2
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `skillsDir` | `string` | `~/.claude/skills` | Directory containing skills |
| `format` | `'text'\|'json'` | `'text'` | Output format |
| `quiet` | `boolean` | `false` | Suppress per-skill stdout |

## Return Value

```json
{
  "healthy": 25,
  "broken": 2,
  "warnings": 1,
  "total": 28,
  "summary": "25 healthy, 2 broken, 1 warning",
  "results": [
    {
      "skill": "test-runner",
      "status": "healthy",
      "checks": { "files": "pass", "frontmatter": "pass", "package": "pass", "exports": "pass" }
    },
    {
      "skill": "broken-skill",
      "status": "broken",
      "checks": { "files": "fail", "frontmatter": "skip", "package": "skip", "exports": "skip" },
      "errors": ["Missing index.js"]
    }
  ]
}
```
