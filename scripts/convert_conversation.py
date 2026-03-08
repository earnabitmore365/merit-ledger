#!/usr/bin/env python3
"""
将 Claude Code 的 JSONL 对话记录转换为可读的 Markdown 格式
"""

import json
import sys
import os
from datetime import datetime


def extract_text_from_content(content):
    """从 content 提取可读文本"""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    text = block.get("text", "")
                    if text and not text.startswith("<system-reminder>"):
                        parts.append(text)
                elif btype == "thinking":
                    # 跳过思考过程（太长）
                    pass
                elif btype == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})
                    if tool_name == "Read":
                        parts.append(f"> 📖 读取文件: `{tool_input.get('file_path', '')}`")
                    elif tool_name == "Write":
                        parts.append(f"> ✏️ 写入文件: `{tool_input.get('file_path', '')}`")
                    elif tool_name == "Edit":
                        parts.append(f"> 🔧 编辑文件: `{tool_input.get('file_path', '')}`")
                    elif tool_name == "Bash":
                        desc = tool_input.get("description", "")
                        cmd = tool_input.get("command", "")[:300]
                        if desc:
                            parts.append(f"> 💻 {desc}\n> ```\n> {cmd}\n> ```")
                        else:
                            parts.append(f"> 💻 执行命令\n> ```\n> {cmd}\n> ```")
                    elif tool_name == "Grep":
                        parts.append(f"> 🔍 搜索: `{tool_input.get('pattern', '')}`")
                    elif tool_name == "Glob":
                        parts.append(f"> 📁 查找文件: `{tool_input.get('pattern', '')}`")
                    elif tool_name == "WebSearch":
                        parts.append(f"> 🌐 搜索: {tool_input.get('query', '')}")
                    elif tool_name == "WebFetch":
                        parts.append(f"> 🌐 获取: {tool_input.get('url', '')}")
                    elif tool_name == "Task":
                        desc = tool_input.get("description", "")
                        prompt = tool_input.get("prompt", "")[:200]
                        parts.append(f"> 🤖 子任务: {desc}\n> {prompt}")
                    elif tool_name == "AskUserQuestion":
                        questions = tool_input.get("questions", [])
                        for q in questions:
                            if isinstance(q, dict):
                                parts.append(f"> ❓ {q.get('question', '')}")
                            elif isinstance(q, str):
                                parts.append(f"> ❓ {q}")
                    else:
                        parts.append(f"> 🔧 {tool_name}")
                elif btype == "tool_result":
                    # 简化工具结果
                    pass
            elif isinstance(block, str):
                if not block.startswith("<system-reminder>"):
                    parts.append(block)
        return "\n\n".join(p for p in parts if p)
    return ""


def convert_jsonl_to_markdown(jsonl_path, output_path):
    """将 JSONL 对话转换为 Markdown"""
    conversation = []

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            timestamp = msg.get("timestamp", "")

            # 用户消息
            if msg_type == "user":
                message = msg.get("message", {})
                content = message.get("content", "")
                text = extract_text_from_content(content)
                if text and len(text) > 5:
                    conversation.append({
                        "role": "user",
                        "text": text,
                        "timestamp": timestamp
                    })

            # 助手消息
            elif msg_type == "assistant":
                message = msg.get("message", {})
                content = message.get("content", [])
                text = extract_text_from_content(content)
                if text and len(text) > 3:
                    conversation.append({
                        "role": "assistant",
                        "text": text,
                        "timestamp": timestamp
                    })

            # 压缩摘要
            elif msg_type == "summary":
                summary_msg = msg.get("message", {})
                content = summary_msg.get("content", "")
                if content:
                    text = extract_text_from_content(content) if isinstance(content, list) else str(content)
                    if text:
                        conversation.append({
                            "role": "system",
                            "text": text,
                            "timestamp": timestamp
                        })

    # 合并连续的同角色消息
    merged = []
    for msg in conversation:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["text"] += "\n\n" + msg["text"]
        else:
            merged.append(msg)

    # 写入 Markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# 交易策略讨论完整记录\n\n")
        f.write(f"> 会话ID: `{os.path.basename(jsonl_path).replace('.jsonl', '')}`\n")
        f.write(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"> 消息数: {len(merged)}\n\n")
        f.write("---\n\n")

        for msg in merged:
            role = msg["role"]
            text = msg["text"]
            ts = msg.get("timestamp", "")

            # 格式化时间
            time_str = ""
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    time_str = f" ({dt.strftime('%m-%d %H:%M')})"
                except:
                    pass

            if role == "system":
                f.write(f"### 📋 上下文压缩摘要{time_str}\n\n")
                # 截取摘要的前5000字符
                f.write(text[:5000])
                if len(text) > 5000:
                    f.write("\n\n...[摘要已截断]...")
                f.write("\n\n---\n\n")
            elif role == "user":
                f.write(f"## 👤 用户{time_str}\n\n{text}\n\n---\n\n")
            elif role == "assistant":
                f.write(f"## 🤖 Claude{time_str}\n\n{text}\n\n---\n\n")

    print(f"转换完成: {len(merged)} 条消息 → {output_path}")
    file_size = os.path.getsize(output_path)
    print(f"文件大小: {file_size / 1024:.1f} KB")
    return len(merged)


if __name__ == "__main__":
    jsonl_path = sys.argv[1] if len(sys.argv) > 1 else ""
    output_path = sys.argv[2] if len(sys.argv) > 2 else "conversation.md"

    if not jsonl_path or not os.path.exists(jsonl_path):
        print(f"Usage: python3 {sys.argv[0]} <input.jsonl> [output.md]")
        sys.exit(1)

    convert_jsonl_to_markdown(jsonl_path, output_path)
