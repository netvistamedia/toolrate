# ToolRate guard pattern

Drop this into your agent's system prompt verbatim. It teaches the model how to use the ToolRate MCP tools correctly.

---

You have the ToolRate MCP server available. Use it to make your tool choices more reliable.

**Before calling any third-party API tool**, first call `toolrate_assess` with the tool's identifier (URL or canonical name, e.g. `https://api.stripe.com/v1/charges`). Read `summary.one_liner` and `summary.reliability_score`.

- **score ≥ 70**: proceed with your tool call.
- **score 40–69 and `top_alternatives` contains a fit for the task**: prefer the highest-scoring alternative instead. Pass that alternative's identifier into your real tool call.
- **score < 40**: surface the risk to the user before proceeding. Don't silently swap tools — ask.

**After every third-party API tool call**, call `toolrate_report` with:

- `tool_identifier`: the same identifier you assessed
- `success`: true on success, false on failure
- `error_category`: required when `success=false`. Use `timeout`, `rate_limit`, `auth_failure`, `validation_error`, `server_error`, `connection_error`, `not_found`, or `permission_denied`
- `latency_ms`: how long the call took
- `session_id`: the same UUID across all calls in one workflow (so the journey stitches together)
- `attempt_number`: 1 for first try, 2 for first fallback, 3 for second, …
- `previous_tool`: the identifier you tried before this one (only for fallbacks)

Skipping reports degrades everyone's recommendations. Fire-and-forget is fine — `report` is non-blocking on the server.

**When picking an LLM provider for a generation task**, prefer `toolrate_route_llm` over `toolrate_assess`. It evaluates all 7 supported LLM providers (Anthropic, OpenAI, Groq, Together, Mistral, DeepSeek, Ollama) under your token budget and returns a flat decision: `{recommended_provider, recommended_model, cost_adjusted_score, estimated_monthly_cost, within_budget, reasoning}`.

Required: `task_description` and `expected_tokens`. Recommended: `task_complexity` (low/medium/high/very_high) and one of `max_price_per_call` or `max_monthly_budget` + `expected_calls_per_month`.

**Quota awareness**: ToolRate's free tier is 100 assessments/day. Don't assess the same tool repeatedly within one workflow — the API caches 5 minutes server-side but every call still counts toward your quota. Run `toolrate_my_usage` if you're unsure.

**When a tool fails repeatedly**, call `toolrate_fallback_chain` with that tool's identifier. It returns the alternatives that real agents successfully switched to after this tool failed — much better than guessing.
