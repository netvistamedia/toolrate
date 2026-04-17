"""Canonical tool-category names and alias normalization.

The data pool historically accumulated three or four spellings for the same
bucket: `"payment"` (seed.py), `"payment_apis"` (early imports),
`"Payment APIs"` (LLM assessor), plus stray `"other"`/`"miscellaneous"`.
The 2026-04-14 category-merge collapsed everything in Postgres down to the
canonical Title-Case names below. This module is the single writer-side
guard — every path that sets `Tool.category` funnels through
`normalize_category` so a rerun of seed.py or import_assessments.py can't
resurrect the variant spellings.
"""

CANONICAL_CATEGORIES: frozenset[str] = frozenset({
    "Payment APIs",
    "Email APIs",
    "LLM APIs",
    "Search APIs",
    "Messaging",
    "Cloud Storage",
    "Databases & BaaS",
    "Vector Databases",
    "Auth & Identity",
    "Monitoring & Analytics",
    "Developer Tools",
    "CRM & Productivity",
    "Maps & Location",
    "Web Scraping",
    "Browser Automation",
    "Image/Media Generation",
    "Code Execution",
    "E-commerce",
    "Other APIs",
})


# Alias map: lowercase variant → canonical. Covers every short name used
# by seed.py / import_assessments.py / the 2026-04-14 merge plus common
# spellings an LLM assessor might emit. Keys must be lowercase; the lookup
# lower-cases its input.
_ALIASES: dict[str, str] = {
    # Payment
    "payment":              "Payment APIs",
    "payments":             "Payment APIs",
    "payment_apis":         "Payment APIs",
    # LLM / ML inference
    "llm":                  "LLM APIs",
    "llms":                 "LLM APIs",
    "llm_apis":             "LLM APIs",
    "ml_inference":         "LLM APIs",
    "ml":                   "LLM APIs",
    "ai":                   "LLM APIs",
    # Search
    "search":               "Search APIs",
    "search_apis":          "Search APIs",
    # Email
    "email":                "Email APIs",
    "email_apis":           "Email APIs",
    # Messaging / SMS / streams
    "messaging":            "Messaging",
    "message":              "Messaging",
    "sms":                  "Messaging",
    "chat":                 "Messaging",
    # Cloud Storage
    "storage":              "Cloud Storage",
    "cloud_storage":        "Cloud Storage",
    # Databases & BaaS
    "database":             "Databases & BaaS",
    "databases":            "Databases & BaaS",
    "db":                   "Databases & BaaS",
    "databases_baas":       "Databases & BaaS",
    "baas":                 "Databases & BaaS",
    # Vector Databases
    "vector_db":            "Vector Databases",
    "vector_dbs":           "Vector Databases",
    "vector_databases":     "Vector Databases",
    "vectordb":             "Vector Databases",
    # Auth & Identity
    "auth":                 "Auth & Identity",
    "auth_identity":        "Auth & Identity",
    "identity":             "Auth & Identity",
    "oauth":                "Auth & Identity",
    # Monitoring & Analytics
    "monitoring":           "Monitoring & Analytics",
    "analytics":            "Monitoring & Analytics",
    "monitoring_analytics": "Monitoring & Analytics",
    "observability":        "Monitoring & Analytics",
    # Developer Tools
    "developer":            "Developer Tools",
    "developer_tools":      "Developer Tools",
    "devtools":             "Developer Tools",
    # CRM & Productivity
    "crm":                  "CRM & Productivity",
    "productivity":         "CRM & Productivity",
    "crm_productivity":     "CRM & Productivity",
    # Maps & Location
    "maps":                 "Maps & Location",
    "maps_location":        "Maps & Location",
    "location":             "Maps & Location",
    "geocoding":            "Maps & Location",
    # Web Scraping
    "scraping":             "Web Scraping",
    "web_scraping":         "Web Scraping",
    "scraper":              "Web Scraping",
    # Browser Automation
    "browser_automation":   "Browser Automation",
    "browser":              "Browser Automation",
    "headless":             "Browser Automation",
    # Image / Media Generation
    "image_gen":            "Image/Media Generation",
    "image_generation":     "Image/Media Generation",
    "media_generation":     "Image/Media Generation",
    "image":                "Image/Media Generation",
    # Code Execution
    "code_execution":       "Code Execution",
    "code":                 "Code Execution",
    "sandbox":              "Code Execution",
    # E-commerce
    "ecommerce":            "E-commerce",
    "e-commerce":           "E-commerce",
    "ecom":                 "E-commerce",
    "e_commerce":           "E-commerce",
    # Other — everything unfamiliar funnels into the single "Other APIs"
    # bucket. "Other" used to be a separate canonical, which quietly
    # fragmented the taxonomy (the fallback at the bottom of normalize_category
    # always returned "Other APIs" while these aliases returned "Other").
    "other":                "Other APIs",
    "other_apis":           "Other APIs",
    "miscellaneous":        "Other APIs",
    "misc":                 "Other APIs",
    "unknown":              "Other APIs",
}


def normalize_category(raw: str | None) -> str | None:
    """Map any variant/alias to its canonical Title-Case form.

    - ``None`` or empty string → ``None`` (leave the column NULL)
    - Already-canonical name → returned unchanged
    - Known alias (case-insensitive) → canonical form
    - Case-insensitive canonical match (``"payment apis"``) → canonical form
    - Anything else → ``"Other APIs"`` as a conservative fallback — we'd
      rather bucket a stray spelling into a visible pile than quietly
      fragment the taxonomy again.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    if stripped in CANONICAL_CATEGORIES:
        return stripped
    low = stripped.lower()
    aliased = _ALIASES.get(low)
    if aliased:
        return aliased
    for canon in CANONICAL_CATEGORIES:
        if canon.lower() == low:
            return canon
    return "Other APIs"
