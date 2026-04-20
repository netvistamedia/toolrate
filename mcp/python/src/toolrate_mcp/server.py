"""FastMCP server wiring — registers the 9 ToolRate tools on a ``FastMCP`` instance.

Mirrors ``mcp/typescript/src/server.ts``. ``toolrate_register`` is mounted
conditionally on the absence of ``TOOLRATE_API_KEY`` so a configured setup
cannot accidentally re-register and overwrite an active key.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .client import get_api_key
from .tools import (
    assess,
    categories,
    fallback_chain,
    hidden_gems,
    my_usage,
    register,
    report,
    route_llm,
    search_tools,
)


def build_server() -> FastMCP:
    mcp = FastMCP(name="toolrate")

    # Always-on tools.
    for module in (
        assess,
        report,
        route_llm,
        fallback_chain,
        hidden_gems,
        search_tools,
        categories,
        my_usage,
    ):
        mcp.tool(name=module.NAME, description=module.DESCRIPTION)(module.handler)

    # Bootstrap: only available when no API key is configured. Once a key is
    # set, this tool disappears from the schema so an established setup cannot
    # accidentally re-register and overwrite an active key.
    if not get_api_key():
        mcp.tool(name=register.NAME, description=register.DESCRIPTION)(register.handler)

    return mcp
