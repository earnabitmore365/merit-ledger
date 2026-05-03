#!/usr/bin/env bun
/**
 * Session Query MCP Server — 一键查会话种子
 *
 * Tools:
 *   query_daily    — 按 agent/date/keyword 查 daily md，返回内容或 grep 段落
 *   list_sessions  — 列出所有 agent 的 daily 目录状态（最新文件/时间/大小）
 *
 * 目的: 让太极能独立验证白纱声明，把"懒得查"的路径物理上堵死。
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFileSync, readdirSync, statSync, existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

// ==================== Config ====================

const HOME = homedir();

// Agent → daily 目录列表（多路径的会合并查询）
const AGENT_DIRS: Record<string, string[]> = {
  "太极": [`${HOME}/.claude/projects/-Users-allenbot/memory/daily`],
  "白纱": [
    `${HOME}/.claude/projects/-Volumes-SSD-2TB-project-wuji-auto-trading/memory/daily`,
    `${HOME}/.claude/projects/-Volumes-SSD-2TB-project-auto-trading/memory/daily`,
  ],
  "两仪": [
    `${HOME}/.claude/projects/-Volumes-SSD-2TB-project-wuji-auto-trading/memory/daily`,
    `${HOME}/.claude/projects/-Volumes-SSD-2TB-project-auto-trading/memory/daily`,
  ],
  "merit": [`${HOME}/.claude/projects/-Users-allenbot--claude-merit/memory/daily`],
};

const DEFAULT_MAX_CHARS = 50000;
const KEYWORD_CONTEXT_LINES = 5;

// ==================== Helpers ====================

interface DailyFile {
  path: string;
  agent: string;
  date: string;      // YYYY-MM-DD
  rollIndex: number; // 1 = base file, 2+ = -002.md etc
  mtime: number;     // unix ms
  size: number;
}

// 支持 YYYY-MM-DD.md 和 YYYY-MM-DD-002.md 滚动命名
const ROLL_PATTERN = /^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$/;

function listDailyFiles(dirs: string[], agent: string): DailyFile[] {
  const result: DailyFile[] = [];
  for (const dir of dirs) {
    if (!existsSync(dir)) continue;
    let entries: string[];
    try {
      entries = readdirSync(dir);
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (!entry.endsWith(".md")) continue;
      const m = entry.match(ROLL_PATTERN);
      if (!m) continue;
      const fullPath = join(dir, entry);
      let stat;
      try {
        stat = statSync(fullPath);
      } catch {
        continue;
      }
      result.push({
        path: fullPath,
        agent,
        date: m[1],
        rollIndex: m[2] ? parseInt(m[2], 10) : 1,
        mtime: stat.mtimeMs,
        size: stat.size,
      });
    }
  }
  return result;
}

// 从滚动文件列表中取每个 (agent, date) 组合的最新滚动文件（rollIndex 最大的）
function pickLatestRolling(files: DailyFile[]): DailyFile[] {
  const byKey = new Map<string, DailyFile>();
  for (const f of files) {
    const key = `${f.agent}::${f.date}`;
    const existing = byKey.get(key);
    if (!existing || f.rollIndex > existing.rollIndex) {
      byKey.set(key, f);
    }
  }
  return Array.from(byKey.values());
}

function grepWithContext(content: string, keyword: string, contextLines: number): string {
  const lines = content.split("\n");
  const matchedIndices = new Set<number>();
  const lowerKeyword = keyword.toLowerCase();

  // Find matching lines
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].toLowerCase().includes(lowerKeyword)) {
      for (let j = Math.max(0, i - contextLines); j <= Math.min(lines.length - 1, i + contextLines); j++) {
        matchedIndices.add(j);
      }
    }
  }

  if (matchedIndices.size === 0) return "";

  // Sort and emit with gap markers
  const sorted = Array.from(matchedIndices).sort((a, b) => a - b);
  const output: string[] = [];
  let prevIdx = -2;
  for (const idx of sorted) {
    if (idx > prevIdx + 1 && output.length > 0) {
      output.push("...");
    }
    output.push(`${idx + 1}: ${lines[idx]}`);
    prevIdx = idx;
  }
  return output.join("\n");
}

function truncate(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars) + `\n\n...（已截断，原文 ${text.length} 字符，上限 ${maxChars}）`;
}

// ==================== MCP Server ====================

const server = new Server(
  { name: "session-query", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "query_daily",
      description:
        "查询 agent 的 daily md 会话种子。按 agent/date/keyword 精准定位内容。白纱/两仪会合并两个项目路径。默认只读最新滚动文件（最近上下文），all=true 读当天所有滚动文件合并（用于翻早期对话/channel 消息）。",
      inputSchema: {
        type: "object" as const,
        properties: {
          agent: {
            type: "string",
            description: "agent 名字：太极 / 白纱 / 两仪 / merit。不填则列所有 agent 的最新文件",
            enum: ["太极", "白纱", "两仪", "merit"],
          },
          date: {
            type: "string",
            description: "日期 YYYY-MM-DD。不填取最新",
          },
          keyword: {
            type: "string",
            description: "关键词。提供则只返回包含该关键词的段落及前后 5 行",
          },
          all: {
            type: "boolean",
            description: "默认 false 只读最新滚动文件。true = 读当天所有滚动文件合并返回",
          },
          max_chars: {
            type: "number",
            description: `返回字符上限（默认 ${DEFAULT_MAX_CHARS}）`,
          },
        },
        required: [],
      },
    },
    {
      name: "list_sessions",
      description:
        "列出所有 agent 的 daily 目录状态：每个目录的文件数、最新文件、总大小。用于了解当前有哪些会话可查。",
      inputSchema: {
        type: "object" as const,
        properties: {},
        required: [],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "query_daily") {
    return await handleQueryDaily(args as Record<string, unknown>);
  }
  if (name === "list_sessions") {
    return await handleListSessions();
  }

  return { content: [{ type: "text" as const, text: `Unknown tool: ${name}` }] };
});

// ==================== Tool handlers ====================

async function handleQueryDaily(args: Record<string, unknown>) {
  const agent = args.agent as string | undefined;
  const date = args.date as string | undefined;
  const keyword = args.keyword as string | undefined;
  const allRolls = args.all === true;
  const maxChars = (args.max_chars as number) || DEFAULT_MAX_CHARS;

  // 收集要查的 agent 列表
  const agentsToQuery: string[] = agent ? [agent] : Object.keys(AGENT_DIRS);
  const missingAgents = agentsToQuery.filter((a) => !AGENT_DIRS[a]);
  if (missingAgents.length > 0) {
    return {
      content: [{
        type: "text" as const,
        text: `❌ 未知 agent: ${missingAgents.join(", ")}。可用: ${Object.keys(AGENT_DIRS).join(", ")}`,
      }],
    };
  }

  // 收集所有候选文件
  const allFiles: DailyFile[] = [];
  for (const a of agentsToQuery) {
    const files = listDailyFiles(AGENT_DIRS[a], a);
    allFiles.push(...files);
  }

  if (allFiles.length === 0) {
    return {
      content: [{ type: "text" as const, text: `❌ 未找到任何 daily md 文件（agent=${agentsToQuery.join(",")}）` }],
    };
  }

  // 按 date 筛选或取最新
  // 新格式：同一天可能有多个滚动文件 (YYYY-MM-DD.md, -002.md, -003.md...)
  // 默认只返回最新一个（rollIndex 最大），避免返回过时的早晨对话
  // all=true 时返回该日期所有滚动文件（按 rollIndex 升序）
  let targetFiles: DailyFile[];
  if (date) {
    const sameDate = allFiles.filter((f) => f.date === date);
    if (sameDate.length === 0) {
      const availableDates = Array.from(new Set(allFiles.map((f) => f.date))).sort().slice(-5);
      return {
        content: [{
          type: "text" as const,
          text: `❌ 没有 ${date} 的 daily md。最近 5 个日期: ${availableDates.join(", ")}`,
        }],
      };
    }
    if (allRolls) {
      targetFiles = sameDate.slice().sort((a, b) =>
        a.agent.localeCompare(b.agent) || a.rollIndex - b.rollIndex
      );
    } else {
      targetFiles = pickLatestRolling(sameDate);
    }
  } else {
    // 每个 agent 各取"最新日期"
    const byAgent = new Map<string, string>();  // agent -> latest date
    for (const f of allFiles) {
      const existing = byAgent.get(f.agent);
      if (!existing || f.date > existing) {
        byAgent.set(f.agent, f.date);
      }
    }
    const latestFiles = allFiles.filter((f) => byAgent.get(f.agent) === f.date);
    if (allRolls) {
      targetFiles = latestFiles.slice().sort((a, b) =>
        a.agent.localeCompare(b.agent) || a.rollIndex - b.rollIndex
      );
    } else {
      targetFiles = pickLatestRolling(latestFiles);
    }
  }

  // 按 mtime 降序排
  targetFiles.sort((a, b) => b.mtime - a.mtime);

  // 读取内容（按字符预算分配）
  const sections: string[] = [];
  let remaining = maxChars;
  for (const f of targetFiles) {
    if (remaining <= 0) {
      sections.push(`\n...（字符预算耗尽，跳过 ${targetFiles.length - sections.length} 个文件）`);
      break;
    }
    let content: string;
    try {
      content = readFileSync(f.path, "utf-8");
    } catch (e: any) {
      sections.push(`\n=== ${f.agent} / ${f.date} ===\n❌ 读取失败: ${e.message}`);
      continue;
    }

    let body: string;
    if (keyword) {
      body = grepWithContext(content, keyword, KEYWORD_CONTEXT_LINES);
      if (!body) body = `（未命中关键词 "${keyword}"）`;
    } else {
      body = content;
    }

    const rollLabel = f.rollIndex > 1 ? ` (roll #${f.rollIndex})` : "";
    const header = [
      `=== ${f.agent} / ${f.date}${rollLabel} ===`,
      `路径: ${f.path}`,
      `修改时间: ${new Date(f.mtime).toLocaleString("zh-CN", { timeZone: "Australia/Sydney" })}`,
      `大小: ${(f.size / 1024).toFixed(1)} KB`,
      keyword ? `关键词: "${keyword}" (前后 ${KEYWORD_CONTEXT_LINES} 行上下文)` : "",
      "",
    ].filter(Boolean).join("\n");

    const section = header + body;
    const budgetedSection = truncate(section, remaining);
    sections.push(budgetedSection);
    remaining -= budgetedSection.length;
  }

  return { content: [{ type: "text" as const, text: sections.join("\n\n") }] };
}

async function handleListSessions() {
  const lines: string[] = ["📊 Daily 会话目录状态", ""];

  for (const [agent, dirs] of Object.entries(AGENT_DIRS)) {
    lines.push(`【${agent}】`);
    for (const dir of dirs) {
      if (!existsSync(dir)) {
        lines.push(`  ❌ ${dir}（目录不存在）`);
        continue;
      }
      const files = listDailyFiles([dir], agent);
      if (files.length === 0) {
        lines.push(`  📁 ${dir}（空）`);
        continue;
      }
      files.sort((a, b) => b.mtime - a.mtime);
      const latest = files[0];
      const totalSize = files.reduce((s, f) => s + f.size, 0);
      const latestTime = new Date(latest.mtime).toLocaleString("zh-CN", { timeZone: "Australia/Sydney" });
      const latestRollLabel = latest.rollIndex > 1 ? `-${String(latest.rollIndex).padStart(3, "0")}` : "";
      lines.push(`  📁 ${dir}`);
      lines.push(`     文件数: ${files.length} | 总大小: ${(totalSize / 1024).toFixed(1)} KB`);
      lines.push(`     最新: ${latest.date}${latestRollLabel}.md (${(latest.size / 1024).toFixed(1)} KB, ${latestTime})`);
    }
    lines.push("");
  }

  return { content: [{ type: "text" as const, text: lines.join("\n") }] };
}

// ==================== Start ====================

const transport = new StdioServerTransport();
await server.connect(transport);
