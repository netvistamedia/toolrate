"""ToolRate Python SDK — reliability oracle for AI agents.

Before your agent calls an external tool, check ToolRate for the
reliability score, common pitfalls, and smart alternatives.
"""
from .client import (
    ToolRate,
    AsyncToolRate,
    ToolRateError,
    # Backwards-compatible aliases (the package used to be called `nemoflow`)
    NemoFlowClient,
    AsyncNemoFlowClient,
)
from .guard import guard, toolrate_guard

# Legacy alias for the decorator that used to be called nemoflow_guard
nemoflow_guard = toolrate_guard

__all__ = [
    "ToolRate",
    "AsyncToolRate",
    "ToolRateError",
    "guard",
    "toolrate_guard",
    # Backwards-compat exports
    "NemoFlowClient",
    "AsyncNemoFlowClient",
    "nemoflow_guard",
]
__version__ = "0.6.1"
