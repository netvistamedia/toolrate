# nemoflow (deprecated)

This package has been **renamed to `toolrate`**. It is now a thin
compatibility shim: it depends on `toolrate` and re-exports everything
from it, while emitting a `DeprecationWarning` on import.

## Migration

**Recommended (modern & fastest):**

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add ToolRate to your project
uv add toolrate
```

**Alternative (without uv):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install toolrate
```

> **Note:** If you see a `PEP 668` "externally-managed-environment" error with plain `pip`, that is because of Homebrew Python. Use one of the methods above instead.

```python
# Old
from nemoflow import NemoFlowClient
client = NemoFlowClient("nf_live_...")

# New
from toolrate import ToolRate
client = ToolRate("nf_live_...")
```

The legacy `NemoFlowClient` / `AsyncNemoFlowClient` / `nemoflow_guard`
names still work when imported from either `nemoflow` or `toolrate` —
they are aliases for `ToolRate` / `AsyncToolRate` / `toolrate_guard`.

- **New package:** https://pypi.org/project/toolrate/
- **Docs:** https://api.toolrate.ai/docs
- **Website:** https://toolrate.ai
