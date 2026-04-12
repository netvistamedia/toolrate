# ToolRate TypeScript SDK

TypeScript client for the [ToolRate API](https://api.toolrate.ai) — the reliability oracle for AI agents. Requires Node.js 18+ (uses native `fetch`).

## Installation

```bash
npm install nemoflow
```

## Quick start — one line with guard()

```typescript
import { ToolRate } from "nemoflow";

const nemo = new ToolRate("nf_live_...");

// Wrap any tool call — assess, execute, report, auto-fallback
const result = await nemo.guard(
  "https://api.openai.com/v1/chat/completions",
  () => openai.chat.completions.create({ model: "gpt-4", messages }),
);
```

## Auto-fallback

```typescript
const result = await nemo.guard(
  "https://api.openai.com/v1/chat/completions",
  () => openai.chat.completions.create({ model: "gpt-4", messages }),
  {
    minScore: 50,
    fallbacks: [
      {
        toolIdentifier: "https://api.anthropic.com/v1/messages",
        fn: () => anthropic.messages.create({ model: "claude-sonnet-4-20250514", messages }),
      },
    ],
  },
);
```

## Journey tracking

```typescript
// First attempt fails
await nemo.report({
  toolIdentifier: "https://api.sendgrid.com/v3/mail/send",
  success: false, errorCategory: "rate_limit",
  sessionId: "session-123", attemptNumber: 1,
});

// Fallback succeeds
await nemo.report({
  toolIdentifier: "https://api.resend.com/emails",
  success: true, latencyMs: 180,
  sessionId: "session-123", attemptNumber: 2,
  previousTool: "https://api.sendgrid.com/v3/mail/send",
});
```

## Discovery

```typescript
const gems = await nemo.discoverHiddenGems({ category: "email" });
const chain = await nemo.discoverFallbackChain("https://api.sendgrid.com/v3/mail/send");
```

## Direct API usage

```typescript
const result = await nemo.assess({
  toolIdentifier: "https://api.openai.com/v1/chat/completions",
  context: "customer support chatbot",
});
console.log(result.reliabilityScore);      // 89.0
console.log(result.predictedFailureRisk);  // "low"
console.log(result.topAlternatives);       // [{ tool: "...", score: 90 }]

await nemo.report({
  toolIdentifier: "https://api.openai.com/v1/chat/completions",
  success: true, latencyMs: 2500,
});
```
