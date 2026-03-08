# 工具库（调研备用）

| 工具 | 用途 | 适合场景 | 备注 |
|------|------|----------|------|
| agentchattr | 多AI共享聊天室（@路由） | 黑丝白纱跨窗口协作 | 已配置，待cashflowAPP测试 |
| PicoClaw | 超轻量AI agent（Go，10MB） | 服务端/低配硬件，支持Ollama本地模型 | 不适合手机APP内嵌 |
| react-native-ai | React Native内嵌本地LLM | 手机APP + React Native | 基于MLC LLM引擎 |
| react-native-executorch | React Native内嵌本地LLM | 手机APP + React Native | 基于ExecuTorch，Meta出品 |
| RunAnywhere SDK | 跨框架本地LLM SDK | Flutter / React Native / 原生 | 支持streaming、RAG、函数调用 |
| Gemini Nano-2 | 系统级内置模型 | Android 15原生APP | 免费，无需下载，Android 15内置 |
| Gemma 3 1B | 手机本地模型 | iOS/Android，只要529MB | 速度快，够用 |
| MLC LLM | 手机本地模型引擎 | iOS/Android/浏览器 | 编译模型到各平台 |
| **Cactus SDK** | 本地LLM+工具调用+RAG+语音，一体化 | 手机APP嵌入，完全离线，装好下载一次模型永久用 | YC投资，React Native/Flutter均支持 ⭐最符合需求 |
| picoLLM | 跨平台本地LLM推理引擎 | iOS/Android/Web，完全离线 | Picovoice出品，有Python/Node/Android/iOS SDK |
| Semantic Kernel | 轻量agent框架，嵌入现有应用 | 后端agent，Python/C# | 微软开源，免费 |
| CrewAI | 多agent协作框架 | 多AI角色分工 | 开源免费 |
| LangGraph | 状态图工作流agent | 复杂多步骤任务 | 开源免费 |
| **NexaSDK** | 多模态：文字+视觉+音频，NPU加速，一步出结构化结果 | 拍账单→直接返回{商品,金额}，iOS/Android | 比Cactus更专注多模态 |
| Apple Vision Framework | 系统内置OCR | iOS，免费，只认字不理解 | 可配合LLM做二次理解 |
| Google ML Kit OCR | 系统内置OCR | Android，免费，只认字不理解 | 同上 |
| Whisper（OpenAI开源） | 离线语音转文字，多语言 | 语音记账，本地跑，无需联网 | 可嵌APP，中文支持好 |
| react-native-gifted-charts | 柱/线/饼/环/雷达图 | React Native图表 ⭐ | 最全面，免费 |
| fl_chart | 柱/线/饼/散点图 | Flutter图表 ⭐ | 最流行，高度自定义，免费 |

> cashflowAPP框架由cashflow两仪定，框架定了再选对应SDK。
> 首选方案：Cactus SDK（本地LLM+agent+语音）+ NexaSDK（多模态视觉）+ Gemma 3 1B / LLaMA 3.2 1B-3B
