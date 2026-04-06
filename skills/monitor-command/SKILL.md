---
name: monitor-command
description: Generate macOS .command files for SSH-based remote monitoring of live trading systems. Use when user requests a remote monitor, Mac Mini viewing script, or SSH-based trading dashboard that auto-refreshes. Produces a bash .command file that SSHes to the trading server and runs the monitor.py script.
---

# monitor-command

Generates a macOS `.command` file (double-click in Finder to open Terminal and run).

## Usage

```js
const { generateMonitorCommand, main } = require('./skills/monitor-command');

// Generate with defaults (matches current Nitro config)
generateMonitorCommand();

// Custom config
generateMonitorCommand({
  host: 'localhost',
  port: 2222,
  user: 'pc_heisi_claude',
  monitorScript: '/home/pc_heisi_claude/trading/monitor.py',
  python: '/home/pc_heisi_claude/trading-env/bin/python3',
  interval: 30,
  outputPath: './lab/monitor.command',
  title: 'Auto-Trading Monitor',
});
```

## CLI

```bash
node skills/monitor-command/index.js --host localhost --port 2222 --outputPath lab/monitor.command
```

## Parameters

| Param | Default | Description |
|-------|---------|-------------|
| `host` | `localhost` | SSH hostname or IP |
| `port` | `2222` | SSH port |
| `user` | `pc_heisi_claude` | SSH username |
| `monitorScript` | `/home/pc_heisi_claude/trading/monitor.py` | Remote monitor script |
| `python` | `/home/pc_heisi_claude/trading-env/bin/python3` | Remote Python interpreter |
| `interval` | `30` | Refresh interval (seconds) |
| `outputPath` | `./lab/monitor.command` | Output file path |
| `title` | `Auto-Trading Monitor` | Terminal window title |

## Output

A bash script that:
1. Sets terminal window title
2. Loops: SSH to Nitro → run monitor.py → sleep interval
3. Shows SSH error on connection failure with diagnostic hint
