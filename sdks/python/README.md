# ToolRate Python SDK

Python client for the [ToolRate API](https://api.toolrate.ai) — the reliability oracle for AI agents.

## Installation

We recommend [uv](https://github.com/astral-sh/uv) — the modern Python package manager. It's fast, manages virtual environments for you, and avoids the `externally-managed-environment` errors you'll hit with plain `pip` on macOS Homebrew and recent Linux distros.

```bash
# One-time: install uv (skip if you already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add ToolRate to your project
uv add toolrate
```

Prefer `pip`? Use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install toolrate
```

`poetry`, `pdm`, and `rye` work too: `poetry add toolrate`.

## Quick start — one line of code

The `guard` function wraps any tool call with automatic reliability checking:

```python
from toolrate import ToolRate, guard

client = ToolRate(api_key="nf_live_...")

# Wrap any tool call — assesses before, reports after, automatically
result = guard(client, "https://api.openai.com/v1/chat/completions",
               lambda: openai.chat.completions.create(model="gpt-4", messages=[...]))
```

That's it. ToolRate will:
1. Check the tool's reliability score before calling
2. Execute the tool call
3. Report success/failure back (building the data moat)
4. Classify errors automatically

## Auto-fallback

When a tool fails, automatically try alternatives:

```python
result = guard(
    client,
    "https://api.openai.com/v1/chat/completions",
    lambda: openai.chat.completions.create(model="gpt-4", messages=msgs),
    fallbacks=[
        ("https://api.anthropic.com/v1/messages",
         lambda: anthropic.messages.create(model="claude-sonnet-4-20250514", messages=msgs)),
        ("https://api.groq.com/openai/v1/chat/completions",
         lambda: groq.chat.completions.create(model="llama-3.3-70b", messages=msgs)),
    ],
    min_score=50,  # Skip tools scoring below 50
)
```

## Decorator

```python
from toolrate import ToolRate, toolrate_guard

client = ToolRate(api_key="nf_live_...")

@toolrate_guard(client, "https://api.stripe.com/v1/charges")
def charge_customer(amount, currency):
    return stripe.Charge.create(amount=amount, currency=currency)

# Every call is now automatically assessed + reported
charge_customer(1000, "usd")
```

## Journey tracking

Report fallback patterns to power hidden gem discovery:

```python
# First attempt fails
client.report("https://api.sendgrid.com/v3/mail/send",
    success=False, error_category="rate_limit",
    session_id="session-123", attempt_number=1)

# Fallback succeeds
client.report("https://api.resend.com/emails",
    success=True, latency_ms=180,
    session_id="session-123", attempt_number=2,
    previous_tool="https://api.sendgrid.com/v3/mail/send")
```

## Discovery

Find hidden gems and fallback chains based on real agent behavior:

```python
# Tools that shine as fallbacks
gems = client.discover_hidden_gems(category="email")

# What to try when SendGrid fails
chain = client.discover_fallback_chain("https://api.sendgrid.com/v3/mail/send")
```

## Direct API usage

```python
from toolrate import ToolRate

client = ToolRate(api_key="nf_live_...")

# Assess
result = client.assess("https://api.openai.com/v1/chat/completions",
                        context="customer support chatbot")
print(result["reliability_score"])      # 89.0
print(result["predicted_failure_risk"]) # "low"
print(result["common_pitfalls"])        # ["timeout (8% of failures)"]
print(result["top_alternatives"])       # [{"tool": "...", "score": 90}]

# Report
client.report("https://api.openai.com/v1/chat/completions",
              success=True, latency_ms=2500)

client.close()
```

## Async support

`AsyncToolRate` has the same interface — all methods are `async`.

```python
from toolrate import AsyncToolRate

async with AsyncToolRate(api_key="nf_live_...") as client:
    result = await client.assess("https://api.openai.com/v1/chat/completions")
```
