"""Smoke test: exercise the MCP server via JSON-RPC over stdio.

Matches ``mcp/typescript/smoke.mjs``: asserts 8 tools when TOOLRATE_API_KEY is
set, 9 when it is unset (register included).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys


EXPECTED_BASE = sorted(
    [
        "toolrate_assess",
        "toolrate_categories",
        "toolrate_fallback_chain",
        "toolrate_hidden_gems",
        "toolrate_my_usage",
        "toolrate_report",
        "toolrate_route_llm",
        "toolrate_search_tools",
    ]
)
EXPECTED_WITH_REGISTER = sorted(EXPECTED_BASE + ["toolrate_register"])


async def list_tools(env_overrides: dict[str, str]) -> list[str]:
    env = {**os.environ, **env_overrides}
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "toolrate_mcp",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    def send(msg: dict[str, object]) -> bytes:
        return (json.dumps(msg) + "\n").encode()

    assert proc.stdin is not None and proc.stdout is not None

    proc.stdin.write(
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "smoke", "version": "0.0.0"},
                },
            }
        )
    )
    await proc.stdin.drain()
    await asyncio.sleep(0.2)

    proc.stdin.write(send({"jsonrpc": "2.0", "method": "notifications/initialized"}))
    await proc.stdin.drain()
    await asyncio.sleep(0.1)

    proc.stdin.write(send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}))
    await proc.stdin.drain()

    tools: list[str] = []
    deadline = asyncio.get_event_loop().time() + 5.0
    buffer = b""
    while asyncio.get_event_loop().time() < deadline:
        try:
            chunk = await asyncio.wait_for(proc.stdout.read(4096), timeout=0.5)
        except asyncio.TimeoutError:
            chunk = b""
        if chunk:
            buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line_s = line.decode("utf-8", errors="replace").strip()
            if not line_s:
                continue
            try:
                msg = json.loads(line_s)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == 2 and "result" in msg:
                tools = sorted([t["name"] for t in msg["result"].get("tools", [])])
                break
        if tools:
            break

    proc.stdin.close()
    try:
        await asyncio.wait_for(proc.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    if not tools:
        raise RuntimeError("no tools/list response received")
    return tools


def assert_equal(label: str, actual: list[str], expected: list[str]) -> None:
    if actual != expected:
        print(
            f"FAIL [{label}]:\n  expected: {expected}\n  actual:   {actual}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"OK [{label}]: {len(actual)} tools")


async def main() -> None:
    with_key = await list_tools({"TOOLRATE_API_KEY": "nf_live_smoke_dummy"})
    assert_equal("with key — 8 tools, no register", with_key, EXPECTED_BASE)

    without_key = await list_tools({"TOOLRATE_API_KEY": ""})
    assert_equal("no key — 9 tools, register included", without_key, EXPECTED_WITH_REGISTER)

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
