# ToolRate Tool Assessment Prompt

Use this prompt with each LLM (Claude, GPT-4, Gemini, etc.). Copy the output into a JSON file per LLM, then run the import script.

---

## Prompt

```
You are a senior DevOps engineer and API reliability consultant with 15 years of experience integrating third-party APIs into production systems. You have deep, hands-on experience with hundreds of tools and APIs.

I need you to assess the reliability of popular tools and APIs that AI agents commonly use. For each tool, provide an honest assessment based on your knowledge of real-world failure patterns, documented outages, rate limiting behavior, error rates, and developer community feedback.

Return a JSON array with exactly this structure. Include at least 150 tools across all categories. Be honest — not every API is reliable. Some are genuinely flaky.

Categories to cover:
- LLM APIs (OpenAI, Anthropic, Google, Mistral, Groq, Together, Cohere, etc.)
- Search APIs (Tavily, SerpAPI, Bing, Google, Brave, Exa, etc.)
- Payment APIs (Stripe, PayPal, Square, Lemon Squeezy, Paddle, etc.)
- Email APIs (SendGrid, Mailgun, Resend, Postmark, Amazon SES, etc.)
- Messaging (Slack, Discord, Telegram, Twilio SMS, WhatsApp Business, etc.)
- Cloud Storage (AWS S3, GCS, Azure Blob, Cloudflare R2, etc.)
- Databases & BaaS (Supabase, Firebase, PlanetScale, Neon, Turso, etc.)
- Vector Databases (Pinecone, Qdrant, Weaviate, Chroma, Milvus, etc.)
- Web Scraping (Firecrawl, Browserless, ScrapingBee, Apify, etc.)
- Image/Media Generation (DALL-E, Stability AI, Replicate, Midjourney API, ElevenLabs, etc.)
- Developer Tools (GitHub, GitLab, Vercel, Netlify, Railway, etc.)
- CRM & Productivity (HubSpot, Salesforce, Notion, Airtable, Linear, etc.)
- Maps & Location (Google Maps, Mapbox, HERE, etc.)
- Auth & Identity (Auth0, Clerk, Firebase Auth, Supabase Auth, etc.)
- Monitoring & Analytics (Sentry, Datadog, PostHog, Mixpanel, etc.)
- E-commerce (Shopify, WooCommerce, Medusa, etc.)
- Browser Automation (Playwright cloud, BrowserBase, Steel, etc.)
- Code Execution (E2B, Modal, Replit, etc.)
- Any other APIs that AI agents commonly interact with

For each tool, provide:

```json
[
  {
    "identifier": "https://api.example.com/v1/endpoint",
    "display_name": "Example API",
    "category": "category_name",
    "reliability_estimate": 0.94,
    "avg_latency_ms": 450,
    "common_errors": [
      {"category": "timeout", "frequency": 0.4},
      {"category": "rate_limit", "frequency": 0.35},
      {"category": "server_error", "frequency": 0.15},
      {"category": "auth_failure", "frequency": 0.1}
    ],
    "pitfalls": ["Description of common issue 1", "Description of common issue 2"],
    "mitigations": ["How to prevent/handle issue 1", "How to prevent/handle issue 2"]
  }
]
```

Rules:
- "identifier" must be the actual base API URL or most common endpoint URL
- "reliability_estimate" is 0.0 to 1.0 — the probability a single API call succeeds
- "common_errors" frequencies must sum to 1.0 — this is the distribution AMONG failures only
- Use only these error categories: timeout, rate_limit, server_error, auth_failure, validation_error, connection_error, not_found, permission_denied
- Be brutally honest. If an API is known to be flaky, rate it low. If it's rock-solid, rate it high.
- Include lesser-known but useful APIs that agents use, not just the big names
- avg_latency_ms should reflect real-world P50 latency including network time

Return ONLY the JSON array, no other text.
```

---

## How to use

1. Send this prompt to each LLM:
   - **Claude** → save as `claude_assessment.json`
   - **GPT-4** → save as `gpt4_assessment.json`
   - **Gemini** → save as `gemini_assessment.json`

2. Place the JSON files in `data/assessments/`

3. Run the import script:
   ```bash
   python -m app.import_assessments
   ```
