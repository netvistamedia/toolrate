# `@toolrate/mcp-server`

Official Model Context Protocol server for [ToolRate](https://toolrate.ai) — the reliability oracle for AI agents.

Plug into Claude Code, Cursor, Zed, Windsurf, or any MCP-compatible editor and your agent gets:

- **`toolrate_assess`** — reliability score, pitfalls, mitigations, and best alternatives for any third-party API.
- **`toolrate_route_llm`** — picks the right LLM model+provider under your token budget across 7 providers (Anthropic, OpenAI, Groq, Together, Mistral, DeepSeek, Ollama).
- **`toolrate_report`** — feed real outcomes back so scores stay accurate.
- **`toolrate_fallback_chain`** — what real agents switch to when a tool fails.
- **`toolrate_hidden_gems`** — underrated tools that excel as fallbacks.
- **`toolrate_search_tools`**, **`toolrate_categories`**, **`toolrate_my_usage`** — browse the catalog and watch your quota.

## Setup

You need a free ToolRate API key — get one at [toolrate.ai](https://toolrate.ai), or call the bootstrap `toolrate_register` tool from any MCP client (only available when no key is configured yet).

### Claude Code

```bash
claude mcp add toolrate npx -y @toolrate/mcp-server --env TOOLRATE_API_KEY=nf_live_xxxxx
```

### Cursor — `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "toolrate": {
      "command": "npx",
      "args": ["-y", "@toolrate/mcp-server"],
      "env": {
        "TOOLRATE_API_KEY": "nf_live_xxxxx"
      }
    }
  }
}
```

### Zed — `~/.config/zed/settings.json`

```json
{
  "context_servers": {
    "toolrate": {
      "command": {
        "path": "npx",
        "args": ["-y", "@toolrate/mcp-server"],
        "env": { "TOOLRATE_API_KEY": "nf_live_xxxxx" }
      }
    }
  }
}
```

### Other MCP clients

Anything that speaks MCP over stdio works the same way — point it at `npx -y @toolrate/mcp-server` with `TOOLRATE_API_KEY` in env.

## Tools

| Tool | What it does |
|------|---|
| `toolrate_assess` | Rate a tool's reliability before calling. Returns a `summary` block + 20 detail fields. |
| `toolrate_report` | Report success/failure after a tool call. |
| `toolrate_route_llm` | Pick the best LLM model+provider under your budget. |
| `toolrate_fallback_chain` | Get the best alternatives when a tool fails. |
| `toolrate_hidden_gems` | Discover underrated tools by category. |
| `toolrate_search_tools` | Search/browse the ToolRate catalog. |
| `toolrate_categories` | List all canonical categories. |
| `toolrate_my_usage` | Check your API key quota. |
| `toolrate_register` | (Only when `TOOLRATE_API_KEY` is unset) Register a new key by email. |

## How agents should use this

Drop this into your agent's system prompt — see [`prompts/guard-pattern.md`](./prompts/guard-pattern.md) for the canonical version:

> Before calling any third-party API tool, first call `toolrate_assess` with the tool's identifier (URL or canonical name). Read `summary.reliability_score`.
>
> - If score ≥ 70, proceed.
> - If score < 70 and `top_alternatives` has a fit, use the highest-scoring alternative.
> - If score < 40, surface the risk to the user before proceeding.
>
> After every third-party API tool call, call `toolrate_report` with `{tool_identifier, success, error_category?, latency_ms?}`. This is how ToolRate learns.
>
> When picking an LLM provider for a generation task, prefer `toolrate_route_llm` — it returns the routing fields directly.

### Quota tips

- Free tier is **100 assessments/day**. ToolRate caches scores for ~5 min server-side so calling `assess` for the same tool twice in a row only costs one quota call.
- Run `toolrate_route_llm` once per workflow and reuse the picked model — it costs 1 quota call per provider considered (up to 7).
- Use `toolrate_my_usage` to self-throttle.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TOOLRATE_API_KEY` | Yes (except for `toolrate_register`) | — | Your `nf_live_…` API key. |
| `TOOLRATE_BASE_URL` | No | `https://api.toolrate.ai` | Override for staging/dev. |

## Development

```bash
git clone https://github.com/netvistamedia/toolrate
cd toolrate/mcp/typescript
npm install
npm run build

# Smoke test (verifies tool registration in both with-key and no-key modes)
node smoke.mjs

# Wire into Claude Code locally
claude mcp add toolrate-dev node "$(pwd)/dist/index.js" --env TOOLRATE_API_KEY=nf_live_xxxxx
```

## License

[MIT](./LICENSE) — distinct from the ToolRate API server (BUSL-1.1). The MCP server is permissively licensed so any project can integrate it.
