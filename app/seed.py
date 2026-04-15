"""Seed the database with popular tools and curated reliability data.

Usage:
    python -m app.seed
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import async_session
from app.models.tool import Tool
from app.models.report import ExecutionReport
from app.models.alternative import Alternative
from app.core.categories import normalize_category
from app.core.security import make_fingerprint

# Top tools with curated reliability profiles
# (identifier, display_name, category, base_success_rate, avg_latency_ms)
SEED_TOOLS = [
    # Payment APIs
    ("https://api.stripe.com/v1/charges", "Stripe Charges", "payment", 0.95, 450),
    ("https://api.stripe.com/v1/payment_intents", "Stripe Payment Intents", "payment", 0.96, 400),
    ("https://api.paypal.com/v2/checkout/orders", "PayPal Checkout", "payment", 0.91, 600),
    ("https://api.lemonsqueezy.com/v1/checkouts", "Lemon Squeezy", "payment", 0.94, 350),
    # LLM APIs
    ("https://api.openai.com/v1/chat/completions", "OpenAI Chat", "llm", 0.93, 2500),
    ("https://api.anthropic.com/v1/messages", "Anthropic Messages", "llm", 0.96, 2200),
    ("https://generativelanguage.googleapis.com/v1/models", "Google Gemini", "llm", 0.91, 2800),
    ("https://api.mistral.ai/v1/chat/completions", "Mistral Chat", "llm", 0.92, 1800),
    ("https://api.groq.com/openai/v1/chat/completions", "Groq Chat", "llm", 0.94, 300),
    ("https://api.together.xyz/v1/chat/completions", "Together AI", "llm", 0.90, 1500),
    ("https://api.deepseek.com/v1/chat/completions", "DeepSeek Chat", "llm", 0.91, 1500),
    # Search & Web
    ("https://api.tavily.com/search", "Tavily Search", "search", 0.94, 800),
    ("https://serpapi.com/search", "SerpAPI", "search", 0.93, 1200),
    ("https://api.bing.microsoft.com/v7.0/search", "Bing Search", "search", 0.95, 500),
    ("https://www.googleapis.com/customsearch/v1", "Google Custom Search", "search", 0.94, 600),
    # Communication
    ("https://api.sendgrid.com/v3/mail/send", "SendGrid Email", "email", 0.97, 300),
    ("https://api.mailgun.net/v3/messages", "Mailgun", "email", 0.95, 350),
    ("https://api.resend.com/emails", "Resend Email", "email", 0.96, 250),
    ("https://slack.com/api/chat.postMessage", "Slack Post Message", "messaging", 0.96, 200),
    ("https://discord.com/api/v10/channels/messages", "Discord Send Message", "messaging", 0.93, 300),
    ("https://api.twilio.com/2010-04-01/Messages", "Twilio SMS", "sms", 0.95, 500),
    # Cloud Storage
    ("https://s3.amazonaws.com", "AWS S3", "storage", 0.998, 150),
    ("https://storage.googleapis.com", "Google Cloud Storage", "storage", 0.997, 160),
    ("https://blob.core.windows.net", "Azure Blob Storage", "storage", 0.996, 170),
    # Databases & Data
    ("https://api.supabase.com/rest/v1", "Supabase REST", "database", 0.95, 100),
    ("https://api.airtable.com/v0", "Airtable", "database", 0.93, 400),
    ("https://api.notion.com/v1", "Notion API", "productivity", 0.92, 500),
    # Developer Tools
    ("https://api.github.com", "GitHub API", "developer", 0.96, 300),
    ("https://gitlab.com/api/v4", "GitLab API", "developer", 0.94, 350),
    ("https://api.vercel.com", "Vercel API", "developer", 0.95, 250),
    # Image & Media
    ("https://api.openai.com/v1/images/generations", "DALL-E", "image_gen", 0.88, 8000),
    ("https://api.stability.ai/v1/generation", "Stability AI", "image_gen", 0.87, 6000),
    ("https://api.replicate.com/v1/predictions", "Replicate", "ml_inference", 0.89, 5000),
    # Web Scraping
    ("https://api.firecrawl.dev/v1/scrape", "Firecrawl", "scraping", 0.88, 3000),
    ("https://api.browserless.io/content", "Browserless", "scraping", 0.86, 4000),
    # Maps & Location
    ("https://maps.googleapis.com/maps/api", "Google Maps", "maps", 0.97, 200),
    ("https://api.mapbox.com", "Mapbox", "maps", 0.96, 180),
    # Auth
    ("https://oauth2.googleapis.com/token", "Google OAuth", "auth", 0.98, 150),
    ("https://login.microsoftonline.com/oauth2/v2.0/token", "Microsoft OAuth", "auth", 0.97, 200),
    # Monitoring
    ("https://api.sentry.io", "Sentry", "monitoring", 0.96, 200),
    ("https://api.datadoghq.com/api/v1", "Datadog", "monitoring", 0.95, 250),
    # E-commerce
    ("https://api.shopify.com/admin/api", "Shopify Admin", "ecommerce", 0.94, 400),
    ("https://api.woocommerce.com/wp-json/wc/v3", "WooCommerce", "ecommerce", 0.90, 600),
    # CRM
    ("https://api.hubspot.com/crm/v3", "HubSpot CRM", "crm", 0.94, 350),
    # Vector DBs
    ("https://api.pinecone.io", "Pinecone", "vector_db", 0.93, 80),
    ("https://cloud.qdrant.io", "Qdrant Cloud", "vector_db", 0.92, 60),
    ("https://api.weaviate.io/v1", "Weaviate", "vector_db", 0.91, 70),
]

# Error categories with their typical distribution
ERROR_PROFILES = {
    "payment": [("timeout", 0.3), ("auth_failure", 0.2), ("validation_error", 0.3), ("rate_limit", 0.2)],
    "llm": [("timeout", 0.4), ("rate_limit", 0.35), ("server_error", 0.15), ("validation_error", 0.1)],
    "search": [("timeout", 0.3), ("rate_limit", 0.4), ("server_error", 0.2), ("auth_failure", 0.1)],
    "email": [("validation_error", 0.4), ("auth_failure", 0.3), ("rate_limit", 0.2), ("server_error", 0.1)],
    "messaging": [("rate_limit", 0.4), ("auth_failure", 0.3), ("validation_error", 0.2), ("timeout", 0.1)],
    "sms": [("validation_error", 0.3), ("rate_limit", 0.3), ("auth_failure", 0.2), ("timeout", 0.2)],
    "storage": [("timeout", 0.3), ("permission_denied", 0.3), ("not_found", 0.2), ("server_error", 0.2)],
    "database": [("timeout", 0.3), ("connection_error", 0.3), ("validation_error", 0.2), ("rate_limit", 0.2)],
    "developer": [("rate_limit", 0.4), ("auth_failure", 0.3), ("not_found", 0.2), ("server_error", 0.1)],
    "image_gen": [("timeout", 0.4), ("rate_limit", 0.3), ("server_error", 0.2), ("validation_error", 0.1)],
    "scraping": [("timeout", 0.4), ("connection_error", 0.3), ("server_error", 0.2), ("rate_limit", 0.1)],
    "ml_inference": [("timeout", 0.4), ("server_error", 0.3), ("rate_limit", 0.2), ("validation_error", 0.1)],
    "maps": [("rate_limit", 0.4), ("auth_failure", 0.3), ("validation_error", 0.2), ("timeout", 0.1)],
    "auth": [("validation_error", 0.4), ("server_error", 0.3), ("timeout", 0.2), ("connection_error", 0.1)],
    "monitoring": [("rate_limit", 0.4), ("auth_failure", 0.3), ("timeout", 0.2), ("server_error", 0.1)],
    "ecommerce": [("rate_limit", 0.3), ("timeout", 0.3), ("auth_failure", 0.2), ("validation_error", 0.2)],
    "crm": [("rate_limit", 0.3), ("timeout", 0.3), ("auth_failure", 0.2), ("validation_error", 0.2)],
    "productivity": [("rate_limit", 0.4), ("timeout", 0.3), ("auth_failure", 0.2), ("server_error", 0.1)],
    "vector_db": [("timeout", 0.3), ("connection_error", 0.3), ("rate_limit", 0.2), ("server_error", 0.2)],
}

# Alternatives mapping (by category)
ALTERNATIVE_GROUPS = {
    "payment": ["https://api.stripe.com/v1/charges", "https://api.paypal.com/v2/checkout/orders", "https://api.lemonsqueezy.com/v1/checkouts"],
    "llm": ["https://api.openai.com/v1/chat/completions", "https://api.anthropic.com/v1/messages", "https://api.groq.com/openai/v1/chat/completions", "https://api.mistral.ai/v1/chat/completions", "https://api.deepseek.com/v1/chat/completions"],
    "search": ["https://api.tavily.com/search", "https://serpapi.com/search", "https://api.bing.microsoft.com/v7.0/search"],
    "email": ["https://api.sendgrid.com/v3/mail/send", "https://api.mailgun.net/v3/messages", "https://api.resend.com/emails"],
    "vector_db": ["https://api.pinecone.io", "https://cloud.qdrant.io", "https://api.weaviate.io/v1"],
}


def _pick_error(category: str) -> str:
    profile = ERROR_PROFILES.get(category, [("server_error", 0.5), ("timeout", 0.5)])
    r = random.random()
    cumulative = 0.0
    for error, prob in profile:
        cumulative += prob
        if r <= cumulative:
            return error
    return profile[-1][0]


async def seed():
    now = datetime.now(timezone.utc)
    fingerprint = make_fingerprint("seed", "seed")
    tool_map: dict[str, Tool] = {}

    async with async_session() as db:
        # Create or update tools
        for identifier, display_name, category, _, _ in SEED_TOOLS:
            result = await db.execute(
                select(Tool).where(Tool.identifier == identifier)
            )
            # The SEED_TOOLS list carries short snake-case category labels
            # (e.g. "payment", "llm") that double as ERROR_PROFILES keys. The
            # DB column must hold the canonical Title-Case name, so normalize
            # at the write boundary while keeping `category` itself unchanged
            # for the _pick_error lookup below.
            canonical = normalize_category(category)
            tool = result.scalar_one_or_none()
            if tool:
                tool.display_name = display_name
                tool.category = canonical
            else:
                tool = Tool(
                    identifier=identifier,
                    display_name=display_name,
                    category=canonical,
                )
                db.add(tool)
            tool_map[identifier] = tool

        await db.flush()

        # Generate synthetic reports (50-200 per tool, spread over 30 days)
        total_reports = 0
        for identifier, _, category, success_rate, avg_latency in SEED_TOOLS:
            tool = tool_map[identifier]
            num_reports = random.randint(50, 200)

            for _ in range(num_reports):
                age_days = random.uniform(0, 30)
                created = now - timedelta(days=age_days)
                success = random.random() < success_rate
                latency = max(50, int(random.gauss(avg_latency, avg_latency * 0.3)))

                report = ExecutionReport(
                    tool_id=tool.id,
                    success=success,
                    error_category=None if success else _pick_error(category),
                    latency_ms=latency,
                    context_hash="__global__",
                    reporter_fingerprint=fingerprint,
                    created_at=created,
                )
                db.add(report)
                total_reports += 1

            # Accumulate so re-running the seed on an existing tool keeps
            # the count in sync with the true row count rather than
            # overwriting it with just the latest batch.
            tool.report_count = (tool.report_count or 0) + num_reports

        # Create alternatives. There's no unique constraint on
        # (tool_id, alternative_tool_id), so re-running the seed would
        # otherwise duplicate every pair — check existence first.
        alt_count = 0
        for group in ALTERNATIVE_GROUPS.values():
            for i, ident in enumerate(group):
                for j, alt_ident in enumerate(group):
                    if i == j or ident not in tool_map or alt_ident not in tool_map:
                        continue
                    tool_a = tool_map[ident]
                    tool_b = tool_map[alt_ident]
                    existing = await db.execute(
                        select(Alternative).where(
                            Alternative.tool_id == tool_a.id,
                            Alternative.alternative_tool_id == tool_b.id,
                        )
                    )
                    # .first() — not scalar_one_or_none — because the
                    # `alternatives` table has no unique constraint on this
                    # pair, so a prior run could have left duplicates that
                    # would otherwise crash MultipleResultsFound.
                    if existing.scalars().first() is not None:
                        continue
                    db.add(Alternative(
                        tool_id=tool_a.id,
                        alternative_tool_id=tool_b.id,
                        relevance_score=round(random.uniform(0.6, 0.95), 2),
                    ))
                    alt_count += 1

        await db.commit()

    print(f"Seeded {len(SEED_TOOLS)} tools with {total_reports} reports and {alt_count} alternative mappings.")


if __name__ == "__main__":
    asyncio.run(seed())
