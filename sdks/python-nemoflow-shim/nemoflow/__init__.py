"""Deprecated — the `nemoflow` package has been renamed to `toolrate`.

This module is a compatibility shim. It re-exports everything from
`toolrate` and emits a ``DeprecationWarning`` the first time it is imported.

To migrate::

    # Recommended (modern & fastest):
    curl -LsSf https://astral.sh/uv/install.sh | sh   # one-time
    uv add toolrate

    # Alternative (without uv):
    python3 -m venv .venv
    source .venv/bin/activate
    pip install toolrate

    # old
    from nemoflow import NemoFlowClient
    client = NemoFlowClient("nf_live_...")

    # new
    from toolrate import ToolRate
    client = ToolRate("nf_live_...")

The legacy ``NemoFlowClient`` / ``AsyncNemoFlowClient`` class names still
work when imported from either package — they are aliases for
``ToolRate`` / ``AsyncToolRate``.
"""
import warnings

warnings.warn(
    "The 'nemoflow' package is deprecated and has been renamed to 'toolrate'. "
    "Please run `uv add toolrate` (or `pip install toolrate` inside a venv) "
    "and update your imports from `from nemoflow import NemoFlowClient` to "
    "`from toolrate import ToolRate`. This compatibility shim will be removed "
    "in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the full public surface of toolrate. The aliases
# NemoFlowClient / AsyncNemoFlowClient / nemoflow_guard are defined inside
# toolrate itself, so existing imports keep working unchanged.
from toolrate import *  # noqa: F401, F403, E402
from toolrate import (  # noqa: F401, E402
    AsyncNemoFlowClient,
    AsyncToolRate,
    NemoFlowClient,
    ToolRate,
    guard,
    nemoflow_guard,
    toolrate_guard,
)

__version__ = "0.3.2"
