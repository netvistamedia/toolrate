"""``toolrate_register`` — bootstrap a new API key when TOOLRATE_API_KEY is unset."""
from __future__ import annotations

import json
from typing import Annotated

from pydantic import Field

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_register"

DESCRIPTION = "\n".join(
    [
        "Creates a new ToolRate API key tied to your email and returns it. Only available when TOOLRATE_API_KEY is unset on the MCP server.",
        "",
        "After getting the key: paste it into your MCP server config under env.TOOLRATE_API_KEY and restart the editor. The other 8 ToolRate tools will then become available.",
    ]
)


async def handler(
    email: Annotated[str, Field(description="Your email — used for the API key, not for marketing.")],
) -> str:
    try:
        body, _rate_limit = await api_request(
            method="POST",
            path="/v1/auth/register",
            body={"email": email, "source": "mcp"},
            authenticated=False,
        )
    except Exception as e:
        raise_tool_error(e)

    config_snippet = {
        "mcpServers": {
            "toolrate": {
                "command": "uvx",
                "args": ["toolrate-mcp"],
                "env": {"TOOLRATE_API_KEY": body["api_key"]},
            }
        }
    }

    lines = [
        "ToolRate API key created.",
        "",
        f"API key: {body['api_key']}",
        f"Tier: {body['tier']}",
        f"Daily limit: {body['daily_limit']}",
        "",
        "Add this to your MCP server config and restart the editor:",
        "",
        json.dumps(config_snippet, indent=2),
        "",
        "Save the key now — it cannot be retrieved later.",
    ]
    return "\n".join(lines)
