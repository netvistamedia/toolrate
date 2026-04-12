# nemoflow (deprecated)

This package has been **renamed to `toolrate`**. It is now a thin
compatibility shim: it depends on `toolrate` and re-exports everything
from it, while emitting a `DeprecationWarning` on import.

## Migration

```bash
pip install toolrate
```

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
