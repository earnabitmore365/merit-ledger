---
name: todo-manager
description: Scan codebases for TODO, FIXME, HACK, XXX, and NOTE comments. Produces structured reports with priority ranking, file hotspots, and tag summaries. Use when tracking technical debt, before refactoring, or when auditing code quality.
---

# todo-manager

Scans source files for tagged comments and produces a prioritized technical debt report.

## Tags (by priority)

| Priority | Tag | Meaning |
|----------|-----|---------|
| 0 | FIXME | Broken, needs immediate fix |
| 1 | HACK | Workaround, should be replaced |
| 2 | XXX | Dangerous or fragile code |
| 3 | TODO | Planned improvement |
| 4 | NOTE | Informational annotation |

## Usage

```js
const { main } = require('./skills/todo-manager');

// Scan default (~/.claude)
const report = await main();

// Scan specific directory
const report2 = await main({ rootDir: '/path/to/repo', quiet: true });

// Custom tags and extensions
const report3 = await main({
  rootDir: './src',
  extensions: ['.js', '.ts'],
  tags: ['TODO', 'FIXME'],
});
```

## Output

```json
{
  "rootDir": "/path",
  "filesScanned": 42,
  "totalTodos": 15,
  "tagSummary": { "FIXME": 3, "HACK": 1, "TODO": 8, "NOTE": 3 },
  "hotspots": [{ "file": "src/core.js", "count": 5 }],
  "items": [{ "tag": "FIXME", "text": "handle edge case", "file": "src/core.js", "line": 42 }]
}
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `rootDir` | `~/.claude` | Directory to scan |
| `extensions` | `.js,.ts,.mjs,.cjs,.py,.sh,.md` | File extensions to include |
| `ignorePatterns` | `node_modules,.git,dist,build,.cache` | Directories to skip |
| `maxDepth` | 8 | Maximum directory depth |
| `tags` | `TODO,FIXME,HACK,XXX,NOTE` | Tags to search for |
| `quiet` | false | Suppress console output |
