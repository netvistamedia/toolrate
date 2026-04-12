"""
ToolRate MCP Server — lets Claude Code, Cursor, and other MCP clients
use ToolRate natively as tool-calling capabilities.

Run:
    python -m mcp_server  (stdio mode, for IDE integrations)

Configure in Claude Code settings or .cursor/mcp.json:
    {
      "mcpServers": {
        "nemoflow": {
          "command": "python",
          "args": ["-m", "mcp_server"],
          "env": {
            "NEMOFLOW_API_KEY": "nf_live_...",
            "NEMOFLOW_BASE_URL": "https://api.toolrate.ai"
          }
        }
      }
    }
"""
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ToolRate",
    instructions="Reliability oracle for AI agents — assess tools before calling, report results after.",
)

API_KEY = os.environ.get("NEMOFLOW_API_KEY", "")
BASE_URL = os.environ.get("NEMOFLOW_BASE_URL", "https://api.toolrate.ai")


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        headers={"X-Api-Key": API_KEY},
        timeout=10.0,
    )


@mcp.tool()
def assess_tool(tool_identifier: str, context: str = "") -> dict:
    """Check the reliability of a tool/API before calling it.

    Returns reliability score (0-100), confidence, failure risk,
    common pitfalls, recommended mitigations, and alternatives.

    Args:
        tool_identifier: URL or name of the tool (e.g. "https://api.stripe.com/v1/charges")
        context: Optional workflow context for more specific scoring (e.g. "payment processing")
    """
    with _client() as client:
        resp = client.post("/v1/assess", json={
            "tool_identifier": tool_identifier,
            "context": context,
        })
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def report_result(
    tool_identifier: str,
    success: bool,
    error_category: str | None = None,
    latency_ms: int | None = None,
    context: str = "",
) -> dict:
    """Report the outcome of a tool call to improve reliability data.

    Args:
        tool_identifier: URL or name of the tool that was called
        success: Whether the call succeeded
        error_category: Error type if failed (timeout, rate_limit, auth_failure, validation_error, server_error, connection_error)
        latency_ms: How long the call took in milliseconds
        context: Workflow context
    """
    body = {
        "tool_identifier": tool_identifier,
        "success": success,
        "context": context,
    }
    if error_category:
        body["error_category"] = error_category
    if latency_ms is not None:
        body["latency_ms"] = latency_ms

    with _client() as client:
        resp = client.post("/v1/report", json=body)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def find_hidden_gems(category: str | None = None, limit: int = 10) -> dict:
    """Discover underrated tools that work well as fallbacks.

    These are tools agents switch to after popular ones fail — high success
    rate but not commonly the first choice.

    Args:
        category: Filter by category (e.g. 'email', 'llm', 'payment')
        limit: Max results (1-50)
    """
    params = {"limit": limit}
    if category:
        params["category"] = category

    with _client() as client:
        resp = client.get("/v1/discover/hidden-gems", params=params)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def get_fallback_chain(tool_identifier: str, limit: int = 5) -> dict:
    """Get the best fallback alternatives when a specific tool fails.

    Based on real agent journey data — what tools agents actually switch to.

    Args:
        tool_identifier: The tool to find fallbacks for
        limit: Max results (1-20)
    """
    with _client() as client:
        resp = client.get("/v1/discover/fallback-chain", params={
            "tool_identifier": tool_identifier,
            "limit": limit,
        })
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
def search_tools(query: str = "", category: str | None = None, limit: int = 20) -> dict:
    """Search and browse all rated tools in ToolRate.

    Args:
        query: Search by name or identifier (case-insensitive)
        category: Filter by category
        limit: Max results (1-200)
    """
    params = {"limit": limit}
    if query:
        params["q"] = query
    if category:
        params["category"] = category

    with _client() as client:
        resp = client.get("/v1/tools", params=params)
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run()
