# 对线模式 — 黑丝 vs 白纱

## Context
老板要在群聊系统里加"对线模式"：黑丝白纱就一个话题互相辩论/评审，老板随时可以插嘴或叫停。现有群聊只支持单向广播+旁听emoji，AI之间无法多轮对话。

## 修改文件
唯一文件：`~/.claude/scripts/group_chat.py`（后端+内嵌前端）

---

## 后端改动

### 1. 新增全局状态（~行70，task_queue下方）

```python
debate_state = {
    "active": False,
    "topic": "",
    "participants": [],    # ["黑丝", "白纱"]
    "max_rounds": 3,
    "current_round": 0,
    "phase": "idle",       # idle / initial / rebuttal / ended
    "history": [],         # [{speaker, content, round}]
    "boss_interjections": [],
    "stop_requested": False,
}
debate_lock = threading.Lock()
```

### 2. 新增 `build_debate_prompt()` 函数（call_claude下方）

复用 call_claude 里读 CLAUDE.md/rules/identity 的逻辑（提取为内部helper `_build_base_context(role_name)`），然后拼辩论专用prompt：

- **初始立场**：
  ```
  [辩论模式] 主题：{topic}
  你是{role}。发表你的立场和核心论据。500字以内，直接有力。
  ```
- **反驳轮**：
  ```
  [辩论模式 — 第{N}轮] 主题：{topic}
  对方（{opponent}）说：{opponent_last_reply}
  你上轮说：{your_last_reply}
  {如有老板插话：[老板插话] {text}}
  针对对方漏洞反驳，强化你的论点。500字以内。
  ```

上下文控制：只注入双方各最新一条完整内容，更早的压缩为一行摘要。

### 3. 新增 `process_debate()` 函数（process_message下方）

主循环逻辑：
```
阶段1-初始立场：两个参与者依次发言
阶段2-反驳：循环 max_rounds 轮，每轮双方各说一次
  - 每次发言前检查 stop_requested
  - 每次发言前消费 boss_interjections 队列
  - 发言写入 DB（tags="对线,R{N}"）+ emit new_message
结束：emit 系统消息 + debate_status{active:false}
```

### 4. 修改 `message_worker()` （~行432）

扩展支持 dict 类型任务：
```python
if isinstance(item, dict) and item.get("type") == "debate":
    process_debate(item["topic"], item["participants"], item["max_rounds"], socketio_app)
else:
    # 原有 tuple 逻辑不动
```

### 5. 新增3个SocketIO事件（~行475后）

- `start_debate`：老板发起 → 校验 → 写入老板消息 → 入队 debate 任务
- `debate_interject`：老板插话 → 写入 boss_interjections + 广播插话消息
- `stop_debate`：设 stop_requested=True

### 6. 重构 call_claude 的上下文构建

把 call_claude 里读 CLAUDE.md/rules/identity 的逻辑提取为 `_build_base_context(role_name)` → 返回 prompt_parts 列表。call_claude 和 debate prompt 都复用它。

---

## 前端改动（内嵌HTML字符串内）

### 1. mention-bar 加对线按钮（~行824后）
```html
<button class="mention-btn" id="mbtn-debate" onclick="toggleDebate()"
        style="border-color:#ef4444;color:#ef4444">⚔️ 对线</button>
```

### 2. 对线配置面板（mention-bar下方）
- 选参与者（默认黑丝vs白纱）
- 选轮数（1/2/3/5，默认3）
- 输入框placeholder变为"输入辩论主题..."

### 3. 对线进行中状态栏（typing-bar旁边或替代）
- 显示"⚔️ 对线 第N/M轮"
- 「✋ 插话」按钮（发送当前输入框内容为 debate_interject）
- 「⏹ 结束」按钮

### 4. sendMessage() 分支
```javascript
if (debateConfigMode) { startDebate(); return; }
if (debateActive) { debateInterject(); return; }
// 原有逻辑
```

### 5. CSS
- 对线消息加红色左边框区分（`.msg.debate .msg-bubble { border-left: 3px solid #ef4444 }`）
- 对线状态栏红色底色

### 6. 监听 debate_status 事件
- active=true → 显示状态栏，禁用@按钮，输入框变插话模式
- active=false → 恢复普通模式

---

## 成本控制
- 轮数上限（默认3轮 = 初始2次 + 反驳6次 = 共8次API调用）
- prompt里引导500字以内
- 辩论历史滑动窗口（只保留最近内容，旧的压缩摘要）
- subprocess timeout 沿用180秒

## DB存储
复用现有 messages 表，tags区分：`对线,发起` / `对线,初始立场` / `对线,反驳,R1` / `对线,插话` / `对线,结束`

## 验证
1. 启动 group_chat.py，打开 http://localhost:8080
2. 点⚔️对线 → 选黑丝vs白纱 → 输入主题 → 发送
3. 确认：双方初始立场 → 多轮反驳 → 自动结束
4. 测试中途插话：输入文字点插话，下一个AI能回应老板意见
5. 测试叫停：点⏹，辩论立即停止
6. 手机端竖排适配检查
