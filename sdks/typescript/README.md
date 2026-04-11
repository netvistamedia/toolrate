# NemoFlow SDK

TypeScript SDK for the NemoFlow API. Requires Node.js 18+ (uses native `fetch`).

## Installation

```bash
npm install nemoflow
```

## Quick start

```typescript
import { NemoFlow } from "nemoflow";

const client = new NemoFlow("your-api-key");
```

## Assess a tool

```typescript
const result = await client.assess({
  toolIdentifier: "stripe.charges.create",
  context: "processing a one-time payment",
  samplePayload: { amount: 2000, currency: "usd" },
});

console.log(result.reliabilityScore); // 94
console.log(result.predictedFailureRisk); // "low"
console.log(result.topAlternatives); // [{ tool: "...", score: 97, reason: "..." }]
```

## Report an outcome

```typescript
await client.report({
  toolIdentifier: "stripe.charges.create",
  success: true,
  latencyMs: 200,
  context: "one-time payment",
});
```

## Report a failure

```typescript
await client.report({
  toolIdentifier: "stripe.charges.create",
  success: false,
  errorCategory: "timeout",
  latencyMs: 30000,
  context: "one-time payment",
});
```

## Error handling

```typescript
import { NemoFlow, NemoFlowError } from "nemoflow";

const client = new NemoFlow("your-api-key");

try {
  await client.assess({ toolIdentifier: "some.tool" });
} catch (err) {
  if (err instanceof NemoFlowError) {
    console.error(err.status); // HTTP status code
    console.error(err.body);   // parsed response body
  }
}
```

## Custom base URL

```typescript
const client = new NemoFlow("your-api-key", {
  baseUrl: "https://custom.endpoint.example.com",
});
```
