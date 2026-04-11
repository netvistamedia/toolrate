"""
Discover APIs from public directories and generate LLM assessments.

Fetches API lists from APIs.guru and other sources, filters out tools
already in the database, then uses Claude to assess new ones in batches.

Usage:
    # Dry run — show what would be discovered
    python scripts/discover-apis.py --dry-run

    # Run discovery and import (requires ANTHROPIC_API_KEY env var)
    python scripts/discover-apis.py

    # Limit batch size
    python scripts/discover-apis.py --batch-size 50
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

# Add project root to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Public API directories ──

KNOWN_APIS = [
    # Format: (identifier, display_name, category)
    # APIs commonly used by AI agents but may not be in directories
    ("https://api.perplexity.ai/v1", "Perplexity API", "Search APIs"),
    ("https://api.exa.ai/v1", "Exa Search API", "Search APIs"),
    ("https://api.brave.com/res/v1", "Brave Search API", "Search APIs"),
    ("https://api.firecrawl.dev/v1", "Firecrawl", "Web Scraping"),
    ("https://api.browserless.io/v1", "Browserless", "Web Scraping"),
    ("https://api.apify.com/v2", "Apify", "Web Scraping"),
    ("https://api.scrapingbee.com/v1", "ScrapingBee", "Web Scraping"),
    ("https://api.e2b.dev/v1", "E2B Code Sandbox", "Code Execution"),
    ("https://api.modal.com/v1", "Modal", "Code Execution"),
    ("https://api.replicate.com/v1", "Replicate", "Image/Media Generation"),
    ("https://api.stability.ai/v1", "Stability AI", "Image/Media Generation"),
    ("https://api.elevenlabs.io/v1", "ElevenLabs", "Image/Media Generation"),
    ("https://api.deepgram.com/v1", "Deepgram", "Image/Media Generation"),
    ("https://api.assemblyai.com/v2", "AssemblyAI", "Image/Media Generation"),
    ("https://api.together.xyz/v1", "Together AI", "LLM APIs"),
    ("https://api.mistral.ai/v1", "Mistral AI", "LLM APIs"),
    ("https://api.cohere.ai/v1", "Cohere", "LLM APIs"),
    ("https://api.fireworks.ai/inference/v1", "Fireworks AI", "LLM APIs"),
    ("https://api.deepseek.com/v1", "DeepSeek", "LLM APIs"),
    ("https://api.clerk.com/v1", "Clerk", "Auth & Identity"),
    ("https://api.neon.tech/v1", "Neon Database", "Databases & BaaS"),
    ("https://api.turso.tech/v1", "Turso", "Databases & BaaS"),
    ("https://api.upstash.com/v2", "Upstash", "Databases & BaaS"),
    ("https://api.planetscale.com/v1", "PlanetScale", "Databases & BaaS"),
    ("https://api.qdrant.io/v1", "Qdrant", "Vector Databases"),
    ("https://api.weaviate.io/v1", "Weaviate", "Vector Databases"),
    ("https://api.pinecone.io/v1", "Pinecone", "Vector Databases"),
    ("https://api.railway.app/v1", "Railway", "Developer Tools"),
    ("https://api.fly.io/v1", "Fly.io", "Developer Tools"),
    ("https://api.render.com/v1", "Render", "Developer Tools"),
    ("https://api.posthog.com/v1", "PostHog", "Monitoring & Analytics"),
    ("https://api.mixpanel.com/v2", "Mixpanel", "Monitoring & Analytics"),
    ("https://api.datadog.com/api/v1", "Datadog", "Monitoring & Analytics"),
    ("https://api.linear.app/v1", "Linear", "CRM & Productivity"),
    ("https://api.notion.com/v1", "Notion", "CRM & Productivity"),
    ("https://api.airtable.com/v0", "Airtable", "CRM & Productivity"),
    ("https://api.hubspot.com/v3", "HubSpot", "CRM & Productivity"),
    ("https://api.paddle.com/v1", "Paddle", "Payment APIs"),
    ("https://api.paypal.com/v2", "PayPal", "Payment APIs"),
    ("https://api.square.com/v2", "Square", "Payment APIs"),
    ("https://api.postmark.com/v1", "Postmark", "Email APIs"),
    ("https://api.mailgun.net/v3", "Mailgun", "Email APIs"),
    ("https://email.us-east-1.amazonaws.com", "Amazon SES", "Email APIs"),
    ("https://api.telegram.org/bot", "Telegram Bot API", "Messaging"),
    ("https://graph.facebook.com/v18.0", "WhatsApp Business API", "Messaging"),
    ("https://discord.com/api/v10", "Discord API", "Messaging"),
    ("https://api.shopify.com/v2", "Shopify", "E-commerce"),
    ("https://api.medusa-commerce.com/v1", "Medusa", "E-commerce"),
    ("https://api.browserbase.com/v1", "BrowserBase", "Browser Automation"),
    ("https://steel.dev/api/v1", "Steel", "Browser Automation"),
    ("https://api.unstructured.io/v1", "Unstructured", "Developer Tools"),
    ("https://api.langchain.com/v1", "LangSmith", "Developer Tools"),
    ("https://api.val.town/v1", "Val Town", "Code Execution"),
    ("https://api.deno.com/v1", "Deno Deploy", "Code Execution"),
    ("https://api.here.com/v8", "HERE Maps", "Maps & Location"),
    ("https://api.opencagedata.com/v1", "OpenCage Geocoding", "Maps & Location"),
    ("https://api.weatherapi.com/v1", "WeatherAPI", "Other APIs"),
    ("https://api.worldnewsapi.com/v1", "World News API", "Other APIs"),
    ("https://api.openrouter.ai/v1", "OpenRouter", "LLM APIs"),
    ("https://api.cerebras.ai/v1", "Cerebras", "LLM APIs"),
    ("https://api.sambanova.ai/v1", "SambaNova", "LLM APIs"),
]


async def fetch_apis_guru() -> list[tuple[str, str, str]]:
    """Fetch API list from APIs.guru directory."""
    tools = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://api.apis.guru/v2/list.json")
            if resp.status_code != 200:
                print(f"  APIs.guru returned {resp.status_code}, skipping")
                return []
            data = resp.json()
            for name, info in list(data.items())[:200]:  # Cap at 200
                versions = info.get("versions", {})
                if not versions:
                    continue
                latest = list(versions.values())[-1]
                api_info = latest.get("info", {})
                title = api_info.get("title", name)
                base_url = latest.get("swaggerUrl", "")
                # Try to extract a usable API base URL
                servers = latest.get("servers", [])
                if servers:
                    base_url = servers[0].get("url", base_url)
                elif "link" in latest:
                    base_url = latest["link"]
                if base_url and base_url.startswith("http"):
                    tools.append((base_url, title, "Other APIs"))
        print(f"  APIs.guru: found {len(tools)} APIs")
    except Exception as e:
        print(f"  APIs.guru error: {e}")
    return tools


async def get_existing_identifiers() -> set[str]:
    """Get all tool identifiers already in the database."""
    from app.db.session import async_session
    from app.models.tool import Tool
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(select(Tool.identifier))
        return {row[0] for row in result.all()}


async def assess_with_claude(tools: list[tuple[str, str, str]], api_key: str) -> list[dict]:
    """Send tools to Claude for reliability assessment."""
    import anthropic

    tool_list = "\n".join(f"- {name} ({cat}): {ident}" for ident, name, cat in tools)

    prompt = f"""You are a senior DevOps engineer assessing API reliability for AI agents.

Assess these tools/APIs. For each one, provide an honest reliability assessment based on your knowledge of real-world failure patterns, outages, rate limiting, and developer feedback.

Tools to assess:
{tool_list}

Return a JSON array with this exact structure for each tool:
```json
[
  {{
    "identifier": "the_url_from_the_list",
    "display_name": "Human Name",
    "category": "category_from_the_list",
    "reliability_estimate": 0.94,
    "avg_latency_ms": 450,
    "common_errors": [
      {{"category": "timeout", "frequency": 0.4}},
      {{"category": "rate_limit", "frequency": 0.35}},
      {{"category": "server_error", "frequency": 0.15}},
      {{"category": "auth_failure", "frequency": 0.1}}
    ],
    "pitfalls": ["Issue 1", "Issue 2"],
    "mitigations": ["Fix 1", "Fix 2"]
  }}
]
```

Rules:
- reliability_estimate: 0.0-1.0, probability a single call succeeds
- common_errors frequencies must sum to 1.0 (distribution among failures only)
- Error categories: timeout, rate_limit, server_error, auth_failure, validation_error, connection_error, not_found, permission_denied
- Be honest. Flaky APIs get low scores. Rock-solid ones get high scores.
- avg_latency_ms = real-world P50 latency

Return ONLY the JSON array, no other text."""

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = msg.content[0].text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]

    return json.loads(text)


async def main():
    parser = argparse.ArgumentParser(description="Discover and assess new APIs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be discovered")
    parser.add_argument("--batch-size", type=int, default=30, help="Tools per LLM call")
    parser.add_argument("--anthropic-key", default=None, help="Anthropic API key (or set ANTHROPIC_API_KEY env)")
    args = parser.parse_args()

    import os
    api_key = args.anthropic_key or os.environ.get("ANTHROPIC_API_KEY", "")

    print("=== NemoFlow API Discovery ===\n")

    # 1. Gather candidate APIs
    print("Gathering APIs from sources...")
    candidates = list(KNOWN_APIS)

    guru_apis = await fetch_apis_guru()
    candidates.extend(guru_apis)

    print(f"\nTotal candidates: {len(candidates)}")

    # 2. Filter out existing tools
    print("Checking existing database...")
    existing = await get_existing_identifiers()
    print(f"Existing tools in DB: {len(existing)}")

    new_tools = [(ident, name, cat) for ident, name, cat in candidates if ident not in existing]
    print(f"New tools to assess: {len(new_tools)}")

    if not new_tools:
        print("No new tools to discover!")
        return

    if args.dry_run:
        print("\nNew tools that would be assessed:")
        for ident, name, cat in sorted(new_tools, key=lambda x: x[2]):
            print(f"  [{cat}] {name}: {ident}")
        return

    if not api_key:
        print("Error: Need ANTHROPIC_API_KEY env var or --anthropic-key flag")
        return

    # 3. Assess in batches
    all_assessments = []
    batches = [new_tools[i:i + args.batch_size] for i in range(0, len(new_tools), args.batch_size)]

    for i, batch in enumerate(batches):
        print(f"\nAssessing batch {i + 1}/{len(batches)} ({len(batch)} tools)...")
        try:
            assessments = await assess_with_claude(batch, api_key)
            all_assessments.extend(assessments)
            print(f"  Got {len(assessments)} assessments")
        except Exception as e:
            print(f"  Error: {e}")

    if not all_assessments:
        print("No assessments generated!")
        return

    # 4. Save to file
    output_path = Path("data/assessments/discovered_assessment.json")
    output_path.write_text(json.dumps(all_assessments, indent=2))
    print(f"\nSaved {len(all_assessments)} assessments to {output_path}")

    # 5. Import into database
    print("\nImporting into database...")
    from app.import_assessments import import_to_db

    # Add source metadata
    for a in all_assessments:
        a.setdefault("sources", 1)

    await import_to_db(all_assessments)
    print("\nDiscovery complete!")


if __name__ == "__main__":
    asyncio.run(main())
