# nemoflow (deprecated)

This package has been **renamed to `toolrate`**. It is now a thin
compatibility shim: it depends on `toolrate` and re-exports everything
from it, while logging a deprecation warning on import.

## Migration

```bash
npm install toolrate
```

```typescript
// Old
import { NemoFlow } from "nemoflow";
const client = new NemoFlow("nf_live_...");

// New
import { ToolRate } from "toolrate";
const client = new ToolRate("nf_live_...");
```

The legacy `NemoFlow` export still works when imported from either
`nemoflow` or `toolrate` — it is an alias for `ToolRate`.

- **New package:** https://www.npmjs.com/package/toolrate
- **Docs:** https://api.toolrate.ai/docs
- **Website:** https://toolrate.ai
