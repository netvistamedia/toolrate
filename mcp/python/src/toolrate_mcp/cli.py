"""Entry point for `toolrate-mcp` (console script / `python -m toolrate_mcp`)."""
import sys

from .server import build_server


def main() -> None:
    try:
        build_server().run(transport="stdio")
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:  # pragma: no cover — defensive top-level handler
        sys.stderr.write(f"toolrate-mcp fatal: {exc}\n")
        sys.exit(1)
