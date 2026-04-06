# Plan: 实盘监控命令 monitor.command

## Context

老板要一个 `.command` 文件（macOS 双击即可运行的终端脚本），远程监控 Nitro 上两个实盘进程的状态。包括 regime 切换、信号、持仓、余额等关键信息，实时刷新。

## 实现方案

### 新建文件
`lab/monitor.command` — macOS `.command` 文件（本质是 bash 脚本，双击打开终端自动执行）

### 功能
通过 SSH 到 Nitro，每 30 秒刷新一次，显示：
1. **ETH 1m** 最新 regime / mode / signal / switches / fused
2. **XRP 5m** 最新 signal
3. **余额 + 持仓**（调 BitMEX API）
4. **WebSocket 状态**（最后一次连接/断开时间）
5. **regime 切换历史**（如果有的话，从日志 grep `switches` 变化的行）

### 实现方式
```bash
#!/bin/bash
# 双击打开终端，SSH 到 Nitro 跑监控循环
while true; do
    clear
    echo "=== Auto-Trading 实盘监控 ==="
    echo "$(date)"
    echo ""
    # SSH 到 Nitro 执行监控脚本
    ssh -p 2222 pc_heisi_claude@localhost "python3 /home/pc_heisi_claude/trading/monitor.py"
    echo ""
    echo "30秒后刷新... (Ctrl+C 退出)"
    sleep 30
done
```

同时在 Nitro 上放一个 `monitor.py`，用 Python 读日志 + 查 API：
- 读 ETH 日志最后一条 `regime=` 行
- 读 XRP 日志最后一条 `信号=` 行
- 查 BitMEX API 余额+持仓
- 显示 regime 切换次数 + 最后切换时间

### 涉及文件
- 新建：`lab/monitor.command`（本地 Mac，~15行 bash）
- 新建：Nitro `/home/pc_heisi_claude/trading/monitor.py`（~80行 Python）

### 验证
1. 双击 `monitor.command`，终端打开，显示实时状态
2. 每 30 秒自动刷新
3. regime 切换时能立刻看到 mode 变化
