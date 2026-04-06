# OpenClaw 问题排查记录

## 问题
- 用户让 agents 添加 DeepSeek API 后 Openclaw 崩溃
- 错误原因：agents 把 `providers` 配置放在了根级别，而不是在 `models` 下面

## 解决方案
- 备份文件位置：`~/.openclaw/openclaw.json.bak*`
- 恢复到正确的备份可以解决问题
- OpenRouter 是内置 provider，不需要额外配置 providers

## 备份文件时间（UTC+11 悉尼时间）
- .bak.4 - 14:32
- .bak.3 - 14:31
- .bak.2 - 14:19
- .bak.1 - 13:22
