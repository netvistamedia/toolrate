# NemoFlow Python SDK

Python client for the [NemoFlow API](https://api.nemoflow.ai).

## Installation

```bash
pip install nemoflow
```

## Quick start

### Synchronous usage

```python
from nemoflow import NemoFlowClient

client = NemoFlowClient(api_key="your-api-key")

# Assess a tool
result = client.assess(
    tool_identifier="openai/gpt-4",
    context="production chatbot",
    sample_payload={"prompt": "Hello"},
)
print(result["reliability_score"])  # e.g. 94
print(result["predicted_failure_risk"])  # e.g. "low"

# Report an outcome
client.report(
    tool_identifier="openai/gpt-4",
    success=True,
    latency_ms=200,
    context="production chatbot",
)

client.close()
```

### Async usage

```python
import asyncio
from nemoflow import AsyncNemoFlowClient

async def main():
    async with AsyncNemoFlowClient(api_key="your-api-key") as client:
        result = await client.assess(tool_identifier="openai/gpt-4")
        print(result)

        await client.report(
            tool_identifier="openai/gpt-4",
            success=False,
            error_category="timeout",
            latency_ms=5000,
        )

asyncio.run(main())
```

### Context manager (sync)

```python
from nemoflow import NemoFlowClient

with NemoFlowClient(api_key="your-api-key") as client:
    result = client.assess("openai/gpt-4")
```

## API reference

### `NemoFlowClient(api_key, base_url="https://api.nemoflow.ai", timeout=30.0)`

| Method | Description |
|--------|-------------|
| `assess(tool_identifier, context="", sample_payload=None)` | Assess a tool's reliability. Returns score, confidence, alternatives, and more. |
| `report(tool_identifier, success, error_category=None, latency_ms=None, context="")` | Report a tool execution outcome. |
| `close()` | Close the underlying HTTP connection. |

`AsyncNemoFlowClient` has the same interface but all methods are `async`.
