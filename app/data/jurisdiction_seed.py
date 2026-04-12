"""Manual jurisdiction overrides for well-known tools.

IP geolocation frequently returns the nearest CDN edge (Cloudflare Frankfurt,
Fastly Amsterdam, etc.) instead of the company's legal seat. This file carries
verified, company-level jurisdiction assignments for the top tools so the
hybrid resolver can return high-confidence answers without depending on
either WHOIS or IP lookups.

Key format: the bare hostname as it appears in a tool identifier URL
(no scheme, no path, case-insensitive). Wildcards are NOT supported —
register each hostname explicitly. If two variants point at the same
company (e.g. api.openai.com and openai.com), list both.

Entry fields:
    country        — ISO 3166-1 alpha-2 code
    category       — JurisdictionCategory: EU | Non-EU | GDPR-adequate | High-Risk
    region         — optional city / state for human-readable output
    provider       — optional hosting provider / parent company
    notes          — short explanation of the assignment (audit trail)

When adding a new entry, include the `notes` field so anyone later can
see *why* we assigned this jurisdiction. Sources should be public:
corporate filings, company websites, or Crunchbase.

If an entry is wrong — please open a PR and correct it. Do not silently
remove entries; that erases the audit trail.
"""
from __future__ import annotations

from typing import TypedDict


class SeedEntry(TypedDict, total=False):
    country: str
    category: str
    region: str
    provider: str
    notes: str


# ─── United States (Non-EU) ─────────────────────────────────────────────────
_US_NON_EU: dict[str, SeedEntry] = {
    # LLM APIs
    "api.openai.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "OpenAI Inc.",
        "notes": "OpenAI OpCo, LLC (Delaware). HQ San Francisco. Models served from Azure.",
    },
    "api.anthropic.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Anthropic PBC",
        "notes": "Anthropic PBC (Delaware). HQ San Francisco. Primary data in US.",
    },
    "api.groq.com": {
        "country": "US", "category": "Non-EU", "region": "Mountain View, CA",
        "provider": "Groq Inc.",
        "notes": "Groq Inc. (Delaware). LPU inference hardware hosted in US datacenters.",
    },
    "api.together.xyz": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Together Computer Inc.",
        "notes": "Together AI (Delaware). HQ San Francisco.",
    },
    "api.together.ai": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Together Computer Inc.",
        "notes": "Together AI (Delaware). HQ San Francisco. WHOIS of .ai domains routes through an Iceland proxy — don't trust that signal.",
    },
    "api.fireworks.ai": {
        "country": "US", "category": "Non-EU", "region": "Redwood City, CA",
        "provider": "Fireworks AI Inc.",
        "notes": "Fireworks AI (Delaware). HQ Redwood City.",
    },
    "api.perplexity.ai": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Perplexity AI Inc.",
        "notes": "Perplexity AI (Delaware). HQ San Francisco.",
    },
    "api.replicate.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Replicate Inc.",
        "notes": "Replicate (Delaware). HQ San Francisco.",
    },
    "api.x.ai": {
        "country": "US", "category": "Non-EU", "region": "Palo Alto, CA",
        "provider": "xAI Corp.",
        "notes": "xAI (Nevada). HQ Palo Alto / San Francisco.",
    },
    "api.deepinfra.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "DeepInfra Inc.",
        "notes": "DeepInfra (Delaware). US-only inference.",
    },
    "api.openrouter.ai": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "OpenRouter Inc.",
        "notes": "OpenRouter (Delaware). Routes across providers, main entity US.",
    },
    "api.cerebras.ai": {
        "country": "US", "category": "Non-EU", "region": "Sunnyvale, CA",
        "provider": "Cerebras Systems Inc.",
        "notes": "Cerebras Systems (Delaware).",
    },
    "api.sambanova.ai": {
        "country": "US", "category": "Non-EU", "region": "Palo Alto, CA",
        "provider": "SambaNova Systems Inc.",
        "notes": "SambaNova Systems (Delaware).",
    },
    # Search / web
    "api.tavily.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Tavily",
        "notes": "Tavily (Delaware). Search-for-agents API.",
    },
    "api.exa.ai": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Exa Labs Inc.",
        "notes": "Exa Labs (Delaware).",
    },
    "api.firecrawl.dev": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Firecrawl Inc.",
        "notes": "Firecrawl (Delaware).",
    },
    "api.browserless.io": {
        "country": "US", "category": "Non-EU",
        "provider": "Browserless", "notes": "Browserless Inc.",
    },
    "api.apify.com": {
        "country": "CZ", "category": "EU", "region": "Prague",
        "provider": "Apify Technologies s.r.o.",
        "notes": "Apify Technologies s.r.o., Prague. Czech Republic / EU.",
    },
    "api.scrapingbee.com": {
        "country": "FR", "category": "EU", "region": "Bordeaux",
        "provider": "ScrapingBee SAS",
        "notes": "ScrapingBee SAS, Bordeaux. France / EU.",
    },
    "serpapi.com": {
        "country": "US", "category": "Non-EU", "region": "Austin, TX",
        "provider": "SerpApi LLC",
        "notes": "SerpApi LLC (Texas).",
    },
    # Payments
    "api.stripe.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Stripe Inc.",
        "notes": "Stripe Inc. (Delaware). EU entity Stripe Payments Europe Ltd (Ireland) handles EU transactions but the API endpoint and primary legal seat is US.",
    },
    "api.paypal.com": {
        "country": "US", "category": "Non-EU", "region": "San Jose, CA",
        "provider": "PayPal Holdings Inc.",
        "notes": "PayPal Holdings Inc. (Delaware).",
    },
    "api.squareup.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Block Inc.",
        "notes": "Block Inc. (Delaware), formerly Square.",
    },
    "api.lemonsqueezy.com": {
        "country": "US", "category": "Non-EU", "region": "Delaware",
        "provider": "Lemon Squeezy LLC (Stripe)",
        "notes": "Lemon Squeezy LLC, acquired by Stripe 2024. Delaware entity.",
    },
    "api.paddle.com": {
        "country": "GB", "category": "GDPR-adequate", "region": "London",
        "provider": "Paddle.com Market Ltd",
        "notes": "Paddle.com Market Ltd, London UK. UK has GDPR adequacy decision.",
    },
    # Email / messaging
    "api.sendgrid.com": {
        "country": "US", "category": "Non-EU", "region": "Denver, CO",
        "provider": "Twilio Inc.",
        "notes": "SendGrid, owned by Twilio Inc. (Delaware).",
    },
    "api.mailgun.net": {
        "country": "US", "category": "Non-EU", "region": "San Antonio, TX",
        "provider": "Sinch (formerly Mailgun Technologies)",
        "notes": "Mailgun, now part of Sinch. US entity.",
    },
    "api.resend.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Resend Inc.",
        "notes": "Resend (Delaware).",
    },
    "api.postmarkapp.com": {
        "country": "US", "category": "Non-EU", "region": "Philadelphia, PA",
        "provider": "ActiveCampaign LLC",
        "notes": "Postmark, owned by ActiveCampaign (Delaware).",
    },
    "api.brevo.com": {
        "country": "FR", "category": "EU", "region": "Paris",
        "provider": "Brevo (formerly Sendinblue)",
        "notes": "Brevo SA (formerly Sendinblue), Paris. EU company.",
    },
    "api.twilio.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Twilio Inc.",
        "notes": "Twilio Inc. (Delaware).",
    },
    "slack.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Salesforce Inc.",
        "notes": "Slack Technologies, owned by Salesforce (Delaware).",
    },
    "discord.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Discord Inc.",
        "notes": "Discord Inc. (Delaware).",
    },
    "api.telegram.org": {
        "country": "AE", "category": "Non-EU", "region": "Dubai",
        "provider": "Telegram FZ-LLC",
        "notes": "Telegram FZ-LLC, Dubai. Officially UAE since 2017, previously BVI.",
    },
    "graph.facebook.com": {
        "country": "US", "category": "Non-EU", "region": "Menlo Park, CA",
        "provider": "Meta Platforms Inc.",
        "notes": "Meta Platforms (Delaware). Also runs WhatsApp Business API.",
    },
    # Developer tools
    "api.github.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "GitHub Inc. (Microsoft)",
        "notes": "GitHub Inc., subsidiary of Microsoft (Delaware).",
    },
    "gitlab.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "GitLab Inc.",
        "notes": "GitLab Inc. (Delaware). HQ San Francisco despite distributed team.",
    },
    "api.vercel.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Vercel Inc.",
        "notes": "Vercel Inc. (Delaware).",
    },
    "api.netlify.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Netlify Inc.",
        "notes": "Netlify Inc. (Delaware).",
    },
    "api.fly.io": {
        "country": "US", "category": "Non-EU", "region": "Chicago, IL",
        "provider": "Fly.io Inc.",
        "notes": "Fly.io Inc. (Delaware).",
    },
    "api.railway.app": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Railway Corp.",
        "notes": "Railway Corp. (Delaware).",
    },
    "api.render.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Render Services Inc.",
        "notes": "Render Services Inc. (Delaware).",
    },
    "api.digitalocean.com": {
        "country": "US", "category": "Non-EU", "region": "New York, NY",
        "provider": "DigitalOcean LLC",
        "notes": "DigitalOcean LLC (Delaware).",
    },
    "api.linode.com": {
        "country": "US", "category": "Non-EU", "region": "Philadelphia, PA",
        "provider": "Akamai Linode",
        "notes": "Linode, owned by Akamai (Delaware).",
    },
    # Databases / BaaS
    "api.supabase.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Supabase Inc.",
        "notes": "Supabase Inc. (Delaware). Offers EU regions for customer data.",
    },
    "api.pinecone.io": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Pinecone Systems Inc.",
        "notes": "Pinecone Systems (Delaware).",
    },
    "api.turso.tech": {
        "country": "US", "category": "Non-EU", "region": "Seattle, WA",
        "provider": "ChiselStrike Inc.",
        "notes": "Turso, ChiselStrike Inc. (Delaware).",
    },
    "api.neon.tech": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Neon Inc.",
        "notes": "Neon Inc. (Delaware). Offers EU regions.",
    },
    "api.planetscale.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "PlanetScale Inc.",
        "notes": "PlanetScale Inc. (Delaware).",
    },
    "api.upstash.com": {
        "country": "US", "category": "Non-EU", "region": "Cupertino, CA",
        "provider": "Upstash Inc.",
        "notes": "Upstash Inc. (Delaware). Global Redis/Kafka.",
    },
    # Productivity / CRM
    "api.notion.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Notion Labs Inc.",
        "notes": "Notion Labs Inc. (Delaware).",
    },
    "api.linear.app": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Linear Orbit Inc.",
        "notes": "Linear Orbit Inc. (Delaware).",
    },
    "api.airtable.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Formagrid Inc. (Airtable)",
        "notes": "Formagrid Inc. dba Airtable (Delaware).",
    },
    "api.hubapi.com": {
        "country": "US", "category": "Non-EU", "region": "Cambridge, MA",
        "provider": "HubSpot Inc.",
        "notes": "HubSpot Inc. (Delaware).",
    },
    # Misc
    "api.elevenlabs.io": {
        "country": "GB", "category": "GDPR-adequate", "region": "London",
        "provider": "ElevenLabs Ltd",
        "notes": "ElevenLabs Ltd, London. UK entity, GDPR-adequate jurisdiction.",
    },
    "api.stability.ai": {
        "country": "GB", "category": "GDPR-adequate", "region": "London",
        "provider": "Stability AI Ltd",
        "notes": "Stability AI Ltd, London. UK entity.",
    },
    "api.deepgram.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Deepgram Inc.",
        "notes": "Deepgram Inc. (Delaware).",
    },
    "api.assemblyai.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "AssemblyAI Inc.",
        "notes": "AssemblyAI Inc. (Delaware).",
    },
    "api.modal.com": {
        "country": "US", "category": "Non-EU", "region": "New York, NY",
        "provider": "Modal Labs Inc.",
        "notes": "Modal Labs Inc. (Delaware).",
    },
    "api.e2b.dev": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "FoundryLabs Inc. (E2B)",
        "notes": "E2B / FoundryLabs Inc. (Delaware).",
    },
    "api.clerk.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Clerk Inc.",
        "notes": "Clerk Inc. (Delaware).",
    },
    "api.auth0.com": {
        "country": "US", "category": "Non-EU", "region": "Bellevue, WA",
        "provider": "Okta Inc.",
        "notes": "Auth0, owned by Okta Inc. (Delaware).",
    },
    "api.datadog.com": {
        "country": "US", "category": "Non-EU", "region": "New York, NY",
        "provider": "Datadog Inc.",
        "notes": "Datadog Inc. (Delaware).",
    },
    "api.posthog.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "PostHog Inc.",
        "notes": "PostHog Inc. (Delaware). Offers EU Cloud region.",
    },
    "api.mixpanel.com": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Mixpanel Inc.",
        "notes": "Mixpanel Inc. (Delaware).",
    },
    "api.sentry.io": {
        "country": "US", "category": "Non-EU", "region": "San Francisco, CA",
        "provider": "Functional Software Inc.",
        "notes": "Sentry / Functional Software Inc. (Delaware). Offers EU region.",
    },
}

# ─── European Union (EU) ─────────────────────────────────────────────────
_EU: dict[str, SeedEntry] = {
    "api.mistral.ai": {
        "country": "FR", "category": "EU", "region": "Paris",
        "provider": "Mistral AI",
        "notes": "Mistral AI SAS, Paris. French entity.",
    },
    "api.aleph-alpha.com": {
        "country": "DE", "category": "EU", "region": "Heidelberg",
        "provider": "Aleph Alpha GmbH",
        "notes": "Aleph Alpha GmbH, Heidelberg. German entity.",
    },
    "api.hetzner.cloud": {
        "country": "DE", "category": "EU", "region": "Gunzenhausen",
        "provider": "Hetzner Online GmbH",
        "notes": "Hetzner Online GmbH. German hosting provider.",
    },
    "api.scaleway.com": {
        "country": "FR", "category": "EU", "region": "Paris",
        "provider": "Scaleway SAS",
        "notes": "Scaleway SAS (Iliad group). French cloud provider.",
    },
    "api.ovh.com": {
        "country": "FR", "category": "EU", "region": "Roubaix",
        "provider": "OVH SAS",
        "notes": "OVH SAS. French cloud provider.",
    },
    "api.gcore.com": {
        "country": "LU", "category": "EU", "region": "Luxembourg",
        "provider": "G-Core Labs S.A.",
        "notes": "G-Core Labs SA, Luxembourg entity.",
    },
    "api.lovable.dev": {
        "country": "SE", "category": "EU", "region": "Stockholm",
        "provider": "Lovable AB",
        "notes": "Lovable AB, Stockholm. Swedish entity.",
    },
    "api.weaviate.io": {
        "country": "NL", "category": "EU", "region": "Amsterdam",
        "provider": "SeMI Technologies B.V.",
        "notes": "Weaviate / SeMI Technologies B.V., Amsterdam. Dutch entity.",
    },
    "api.qdrant.tech": {
        "country": "DE", "category": "EU", "region": "Berlin",
        "provider": "Qdrant Solutions GmbH",
        "notes": "Qdrant Solutions GmbH, Berlin. German entity.",
    },
    "api.blaize.app": {
        "country": "DE", "category": "EU",
        "provider": "Blaize GmbH",
        "notes": "Blaize GmbH, German entity.",
    },
    "api.deepl.com": {
        "country": "DE", "category": "EU", "region": "Cologne",
        "provider": "DeepL SE",
        "notes": "DeepL SE, Cologne. German entity.",
    },
    "api.pipedrive.com": {
        "country": "EE", "category": "EU", "region": "Tallinn",
        "provider": "Pipedrive OÜ",
        "notes": "Pipedrive OÜ, Tallinn. Estonian entity (HQ NYC but legal seat EU).",
    },
}

# ─── GDPR-Adequate (Canada, UK, Japan, etc.) ────────────────────────────
_ADEQUATE: dict[str, SeedEntry] = {
    "api.cohere.ai": {
        "country": "CA", "category": "GDPR-adequate", "region": "Toronto",
        "provider": "Cohere Inc.",
        "notes": "Cohere Inc., Toronto. Canadian entity, adequacy decision covers commercial orgs.",
    },
    "api.cohere.com": {
        "country": "CA", "category": "GDPR-adequate", "region": "Toronto",
        "provider": "Cohere Inc.",
        "notes": "Cohere Inc., Toronto. Canadian entity.",
    },
    "api.shopify.com": {
        "country": "CA", "category": "GDPR-adequate", "region": "Ottawa",
        "provider": "Shopify Inc.",
        "notes": "Shopify Inc., Ottawa. Canadian entity, adequacy decision applies.",
    },
    # UK entries also live in _US_NON_EU for Paddle, Stability, ElevenLabs
    # but keeping them there for file organization; the resolver looks up
    # by hostname so location in the file is cosmetic.
}

# ─── High-Risk ──────────────────────────────────────────────────────────
_HIGH_RISK: dict[str, SeedEntry] = {
    "api.deepseek.com": {
        "country": "CN", "category": "High-Risk", "region": "Hangzhou",
        "provider": "DeepSeek AI Ltd.",
        "notes": "DeepSeek, Hangzhou. Chinese entity. Routes data through PRC infrastructure.",
    },
    "api.moonshot.cn": {
        "country": "CN", "category": "High-Risk",
        "provider": "Moonshot AI",
        "notes": "Moonshot AI (Kimi). Chinese entity.",
    },
    "api.qwen.com": {
        "country": "CN", "category": "High-Risk",
        "provider": "Alibaba Cloud",
        "notes": "Qwen by Alibaba. Chinese cloud.",
    },
    "api.yandex.ru": {
        "country": "RU", "category": "High-Risk", "region": "Moscow",
        "provider": "Yandex LLC",
        "notes": "Yandex LLC. Russian entity. Data subject to FSB-accessible jurisdiction.",
    },
}


JURISDICTION_SEED: dict[str, SeedEntry] = {
    **_US_NON_EU,
    **_EU,
    **_ADEQUATE,
    **_HIGH_RISK,
}


def lookup_seed(hostname: str) -> SeedEntry | None:
    """Return a seed entry for the given hostname, or None if no manual override exists."""
    if not hostname:
        return None
    normalized = hostname.strip().lower()
    if normalized in JURISDICTION_SEED:
        return JURISDICTION_SEED[normalized]
    # Also try without a leading 'www.'
    if normalized.startswith("www."):
        bare = normalized[4:]
        if bare in JURISDICTION_SEED:
            return JURISDICTION_SEED[bare]
    return None
