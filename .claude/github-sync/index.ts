#!/usr/bin/env bun
/**
 * GitHub Sync MCP Server — 通用 GitHub 自动同步
 *
 * Tools:
 *   github_sync   — 同步本地目录到 GitHub repo
 *   github_status — 对比本地 vs 远端差异
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFileSync, readdirSync, statSync, existsSync } from "fs";
import { join, relative, resolve } from "path";
import { homedir } from "os";

// ==================== Config ====================

interface RepoConfig {
  remote: string; // "owner/repo"
  local: string;  // local directory path
}

interface Config {
  token_path: string;
  default_branch: string;
  repos: Record<string, RepoConfig>;
  global_ignore: string[];
}

function expandPath(p: string): string {
  return p.replace(/^~/, homedir());
}

function loadConfig(): Config {
  const configPath = join(import.meta.dir, "config.json");
  return JSON.parse(readFileSync(configPath, "utf-8"));
}

function loadToken(config: Config): string {
  // 优先用 gh CLI 的 token（动态获取，不存文件）
  try {
    const result = Bun.spawnSync(["/opt/homebrew/bin/gh", "auth", "token"], { stdout: "pipe", stderr: "pipe" });
    const ghToken = result.stdout.toString().trim();
    if (ghToken && ghToken.startsWith("gh")) return ghToken;
  } catch {}
  // Fallback: 读文件
  const tokenPath = expandPath(config.token_path);
  return readFileSync(tokenPath, "utf-8").trim();
}

// ==================== Ignore matching ====================

// Hardcoded safety net — these NEVER get pushed regardless of config
const HARDCODED_IGNORE = [
  "**/*.db", "**/*.sqlite", "**/*.duckdb", "**/*.parquet",
  "**/.credentials*", "**/.env", "**/.comm_pass",
  "**/*.jsonl", "**/.github_token",
  "**/__pycache__/**", "**/*.pyc",
  "**/*.bak",
];

function matchesPattern(filePath: string, pattern: string): boolean {
  // Convert glob pattern to regex
  let regex = pattern
    .replace(/\./g, "\\.")
    .replace(/\*\*/g, "<<<GLOBSTAR>>>")
    .replace(/\*/g, "[^/]*")
    .replace(/<<<GLOBSTAR>>>/g, ".*")
    .replace(/\?/g, ".");
  return new RegExp(`^${regex}$`).test(filePath) ||
    new RegExp(`(^|/)${regex}($|/)`.replace(/\.\*\.\*/g, ".*")).test(filePath);
}

function shouldIgnore(relPath: string, ignorePatterns: string[]): boolean {
  const allPatterns = [...HARDCODED_IGNORE, ...ignorePatterns];
  for (const pattern of allPatterns) {
    if (matchesPattern(relPath, pattern)) return true;
    // Also check basename match for simple patterns like "*.db"
    const basename = relPath.split("/").pop() || "";
    const simplePattern = pattern.replace(/^\*\*\//, "");
    if (matchesPattern(basename, simplePattern)) return true;
  }
  return false;
}

// ==================== File scanning ====================

function scanLocalFiles(dir: string, ignorePatterns: string[]): Map<string, Buffer> {
  const files = new Map<string, Buffer>();
  const absDir = resolve(expandPath(dir));

  function walk(current: string) {
    let entries: string[];
    try {
      entries = readdirSync(current);
    } catch {
      return;
    }
    for (const entry of entries) {
      const fullPath = join(current, entry);
      const relPath = relative(absDir, fullPath);

      // Skip hidden dirs (except specific ones) and common noise
      if (entry.startsWith(".") && entry !== ".wuji-root") continue;

      let stat;
      try {
        stat = statSync(fullPath);
      } catch {
        continue;
      }

      if (stat.isDirectory()) {
        if (shouldIgnore(relPath + "/", ignorePatterns)) continue;
        walk(fullPath);
      } else if (stat.isFile()) {
        if (shouldIgnore(relPath, ignorePatterns)) continue;
        // Skip files > 1MB (Contents API limit)
        if (stat.size > 1_000_000) continue;
        try {
          files.set(relPath, readFileSync(fullPath));
        } catch {
          // Permission denied etc — skip silently
        }
      }
    }
  }

  walk(absDir);
  return files;
}

// ==================== GitHub API ====================

const API_BASE = "https://api.github.com";

async function githubGet(
  token: string, owner: string, repo: string, path: string,
  branch: string
): Promise<{ sha: string; content: string } | null> {
  const url = `${API_BASE}/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}?ref=${branch}`;
  const resp = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github.v3+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (resp.status === 404) return null;
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`GitHub GET ${path}: ${resp.status} ${text.slice(0, 200)}`);
  }
  const data = await resp.json();
  return { sha: data.sha, content: data.content || "" };
}

async function githubPut(
  token: string, owner: string, repo: string, path: string,
  content: string, message: string, branch: string, sha?: string
): Promise<void> {
  const url = `${API_BASE}/repos/${owner}/${repo}/contents/${encodeURIComponent(path)}`;
  const body: Record<string, string> = {
    message,
    content, // base64
    branch,
  };
  if (sha) body.sha = sha;

  const resp = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github.v3+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`GitHub PUT ${path}: ${resp.status} ${text.slice(0, 200)}`);
  }
}

// Compute GitHub blob SHA from local content (same algorithm GitHub uses)
function gitBlobSha(content: Buffer): string {
  const header = `blob ${content.length}\0`;
  const store = Buffer.concat([Buffer.from(header), content]);
  const hash = new Bun.CryptoHasher("sha1");
  hash.update(store);
  return hash.digest("hex");
}

// ==================== MCP Server ====================

const server = new Server(
  { name: "github-sync", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "github_sync",
      description:
        "同步本地目录到 GitHub repo。自动识别变化的文件，跳过未变文件，排除敏感文件。",
      inputSchema: {
        type: "object" as const,
        properties: {
          repo: {
            type: "string",
            description: "config.json 里的 repo 名（如 merit, auto-trading）",
          },
          message: {
            type: "string",
            description: "commit message（默认 'sync'）",
          },
          branch: {
            type: "string",
            description: "分支名（默认 config.default_branch）",
          },
          dry_run: {
            type: "boolean",
            description: "true = 只看差异不推送",
          },
        },
        required: ["repo"],
      },
    },
    {
      name: "github_status",
      description:
        "对比本地 vs GitHub 远端差异。显示新增、修改、删除、一致的文件列表。",
      inputSchema: {
        type: "object" as const,
        properties: {
          repo: {
            type: "string",
            description: "config.json 里的 repo 名",
          },
          branch: {
            type: "string",
            description: "分支名（默认 config.default_branch）",
          },
        },
        required: ["repo"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "github_sync") {
    return await handleSync(args as Record<string, unknown>);
  }
  if (name === "github_status") {
    return await handleStatus(args as Record<string, unknown>);
  }

  return { content: [{ type: "text", text: `Unknown tool: ${name}` }] };
});

// ==================== Tool handlers ====================

async function handleSync(args: Record<string, unknown>) {
  const config = loadConfig();
  const repoName = args.repo as string;
  const repoConfig = config.repos[repoName];
  if (!repoConfig) {
    const available = Object.keys(config.repos).join(", ");
    return {
      content: [{ type: "text" as const, text: `❌ repo "${repoName}" 不在 config.json 里。可用: ${available}` }],
    };
  }

  const token = loadToken(config);
  const branch = (args.branch as string) || config.default_branch;
  const message = (args.message as string) || "sync";
  const dryRun = args.dry_run === true;
  const [owner, repo] = repoConfig.remote.split("/");
  const localDir = expandPath(repoConfig.local);

  if (!existsSync(localDir)) {
    return {
      content: [{ type: "text" as const, text: `❌ 本地目录不存在: ${localDir}` }],
    };
  }

  const localFiles = scanLocalFiles(localDir, config.global_ignore);
  const output: string[] = [];
  let pushed = 0, skipped = 0, errors = 0;

  for (const [relPath, content] of localFiles) {
    const localSha = gitBlobSha(content);
    try {
      const remote = await githubGet(token, owner, repo, relPath, branch);
      if (remote && remote.sha === localSha) {
        skipped++;
        continue;
      }

      if (dryRun) {
        output.push(`  ${remote ? "📝 修改" : "➕ 新增"}: ${relPath}`);
        pushed++;
        continue;
      }

      const b64 = content.toString("base64");
      const commitMsg = `${message}: ${relPath}`;
      await githubPut(token, owner, repo, relPath, b64, commitMsg, branch, remote?.sha);
      output.push(`  ✅ ${remote ? "更新" : "新增"}: ${relPath}`);
      pushed++;
    } catch (e: any) {
      output.push(`  ❌ ${relPath}: ${e.message?.slice(0, 100)}`);
      errors++;
    }
  }

  const prefix = dryRun ? "🔍 Dry run" : "📊 同步完成";
  const summary = [
    `${prefix}（${repoName} → ${repoConfig.remote}）:`,
    `  ${dryRun ? "待推送" : "推送"}: ${pushed} 个文件`,
    `  跳过（未变）: ${skipped} 个文件`,
    `  本地文件总数: ${localFiles.size}`,
    errors > 0 ? `  ❌ 错误: ${errors}` : "",
    ...output,
  ].filter(Boolean).join("\n");

  return { content: [{ type: "text" as const, text: summary }] };
}

async function handleStatus(args: Record<string, unknown>) {
  const config = loadConfig();
  const repoName = args.repo as string;
  const repoConfig = config.repos[repoName];
  if (!repoConfig) {
    const available = Object.keys(config.repos).join(", ");
    return {
      content: [{ type: "text" as const, text: `❌ repo "${repoName}" 不在 config.json 里。可用: ${available}` }],
    };
  }

  const token = loadToken(config);
  const branch = (args.branch as string) || config.default_branch;
  const [owner, repo] = repoConfig.remote.split("/");
  const localDir = expandPath(repoConfig.local);

  if (!existsSync(localDir)) {
    return {
      content: [{ type: "text" as const, text: `❌ 本地目录不存在: ${localDir}` }],
    };
  }

  const localFiles = scanLocalFiles(localDir, config.global_ignore);
  const added: string[] = [];
  const modified: string[] = [];
  const same: string[] = [];
  let errors = 0;

  for (const [relPath, content] of localFiles) {
    const localSha = gitBlobSha(content);
    try {
      const remote = await githubGet(token, owner, repo, relPath, branch);
      if (!remote) {
        added.push(relPath);
      } else if (remote.sha !== localSha) {
        modified.push(relPath);
      } else {
        same.push(relPath);
      }
    } catch {
      errors++;
    }
  }

  const summary = [
    `📊 状态（${repoName}: ${repoConfig.remote}@${branch}）:`,
    `  ➕ 新增: ${added.length}`,
    `  📝 修改: ${modified.length}`,
    `  ✅ 一致: ${same.length}`,
    errors > 0 ? `  ❌ 查询错误: ${errors}` : "",
    added.length > 0 ? `\n新增文件:\n${added.map((f) => `  + ${f}`).join("\n")}` : "",
    modified.length > 0 ? `\n修改文件:\n${modified.map((f) => `  ~ ${f}`).join("\n")}` : "",
  ].filter(Boolean).join("\n");

  return { content: [{ type: "text" as const, text: summary }] };
}

// ==================== Start ====================

const transport = new StdioServerTransport();
await server.connect(transport);
