# ToolRate MCP servers

This directory contains the official Model Context Protocol servers for [ToolRate](https://toolrate.ai).

| Language | Package | Status | Install |
|---|---|---|---|
| TypeScript | [`@toolrate/mcp-server`](./typescript) | v0.1.0 | `npx -y @toolrate/mcp-server` |
| Python | `toolrate-mcp` | planned, week 2 | `uvx toolrate-mcp` |

Both expose the same 8 tools and read the same `TOOLRATE_API_KEY` env var. Pick whichever runtime your editor's MCP integration prefers.

See [`typescript/README.md`](./typescript/README.md) for setup snippets (Claude Code, Cursor, Zed) and the tool reference.
