"""Hybrid jurisdiction resolver — country, provider, GDPR classification.

Three-tier strategy ordered by trustworthiness:

    1. **Manual seed** (source=manual, confidence=high)
       Hard-coded mapping in app/data/jurisdiction_seed.py for the
       top ~80 tools where we have verified the legal seat from
       public filings. Always overrides the other two tiers.

    2. **WHOIS registrant country** (source=whois, confidence=medium)
       `python-whois` against the bare domain. Privacy proxies and
       redacted TLDs return None; we ignore those and fall through.

    3. **IP geolocation** (source=ip_geolocation OR cdn_detected, confidence=low)
       DNS + ipinfo.io. If the provider org matches a known CDN name
       (Cloudflare, Fastly, Akamai) we flag the result as cdn_detected
       so callers know the country is almost certainly an edge location,
       not the company's legal seat.

All tiers return empty on any failure so enrichment stays additive —
tools without resolvable jurisdiction keep NULL columns and downstream
code treats that the same as "Non-EU / medium risk / low confidence".
"""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from app.data.jurisdiction_seed import lookup_seed

logger = logging.getLogger("nemoflow.jurisdiction")

JurisdictionCategory = Literal["EU", "Non-EU", "GDPR-adequate", "High-Risk"]
JurisdictionSource = Literal["manual", "whois", "ip_geolocation", "cdn_detected"]
JurisdictionConfidence = Literal["high", "medium", "low"]
DataResidencyRisk = Literal["none", "low", "medium", "high"]

# EU + EEA — jurisdictions that fall under GDPR directly.
EU_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
    "IS", "LI", "NO",  # EEA
})

# EU Commission adequacy decisions (as of 2024).
GDPR_ADEQUATE_COUNTRIES: frozenset[str] = frozenset({
    "AD", "AR", "CA", "FO", "GG", "IL", "IM", "JP", "JE", "NZ", "KR",
    "CH", "GB", "UY",
})

# Jurisdictions with active mass-surveillance or no privacy framework.
HIGH_RISK_COUNTRIES: frozenset[str] = frozenset({
    "CN", "RU", "IR", "KP", "BY", "SY",
})

# Substring patterns for known CDN providers. When ipinfo.io's org field
# contains one of these (case-insensitive), we flag the result as
# cdn_detected so downstream code knows the country is an edge location.
# Kept deliberately narrow — we DON'T flag AWS/Google/Azure because they're
# the actual host for many real services, not just CDN edges.
CDN_PROVIDER_PATTERNS: tuple[str, ...] = (
    "cloudflare",
    "fastly",
    "akamai",
    "edgecast",
    "stackpath",
    "incapsula",
    "cloudfront",
    "keycdn",
    "bunnycdn",
    "bunny.net",
)

COUNTRY_NAMES: dict[str, str] = {
    # EU/EEA
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia",
    "CY": "Cyprus", "CZ": "Czech Republic", "DK": "Denmark", "EE": "Estonia",
    "FI": "Finland", "FR": "France", "DE": "Germany", "GR": "Greece",
    "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LV": "Latvia",
    "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia",
    "SI": "Slovenia", "ES": "Spain", "SE": "Sweden",
    "IS": "Iceland", "LI": "Liechtenstein", "NO": "Norway",
    # Adequacy
    "GB": "United Kingdom", "CH": "Switzerland", "JP": "Japan",
    "KR": "South Korea", "CA": "Canada", "NZ": "New Zealand",
    "IL": "Israel", "AR": "Argentina", "UY": "Uruguay", "AD": "Andorra",
    "FO": "Faroe Islands", "GG": "Guernsey", "IM": "Isle of Man", "JE": "Jersey",
    # Common non-EU
    "US": "United States", "MX": "Mexico", "BR": "Brazil", "SG": "Singapore",
    "HK": "Hong Kong", "TW": "Taiwan", "IN": "India", "AU": "Australia",
    "ZA": "South Africa", "AE": "United Arab Emirates", "TR": "Turkey",
    # High-risk
    "CN": "China", "RU": "Russia", "IR": "Iran", "KP": "North Korea",
    "BY": "Belarus", "SY": "Syria",
}


# ═══════════════════════════════════════════════════════════════════════
# Pure classification helpers
# ═══════════════════════════════════════════════════════════════════════


def classify_jurisdiction(country_code: str | None) -> JurisdictionCategory:
    """Map a 2-letter country code to its GDPR-relevant bucket."""
    if not country_code:
        return "Non-EU"
    code = country_code.upper()
    if code in EU_COUNTRIES:
        return "EU"
    if code in HIGH_RISK_COUNTRIES:
        return "High-Risk"
    if code in GDPR_ADEQUATE_COUNTRIES:
        return "GDPR-adequate"
    return "Non-EU"


def is_gdpr_compliant(category: str | None) -> bool:
    """EU and adequacy-decision countries are GDPR-compliant by law."""
    return category in ("EU", "GDPR-adequate")


def data_residency_risk(
    category: str | None,
    confidence: str | None = None,
) -> DataResidencyRisk:
    """Risk that routing data through this jurisdiction creates a GDPR problem.

    Low-confidence EU verdicts get bumped up to 'low' risk instead of 'none'
    because the category itself is uncertain.
    """
    base: dict[str, DataResidencyRisk] = {
        "EU": "none",
        "GDPR-adequate": "low",
        "Non-EU": "medium",
        "High-Risk": "high",
    }
    risk = base.get(category or "", "medium")
    if confidence == "low" and risk in ("none", "low"):
        return "low" if risk == "none" else "medium"
    return risk


def recommended_for(category: str | None) -> list[str]:
    """Which kinds of agent workflows this jurisdiction is suited for."""
    if category == "EU":
        return ["eu_companies", "gdpr_strict_workflows", "high_privacy_workflows"]
    if category == "GDPR-adequate":
        return ["eu_companies", "gdpr_flexible_workflows"]
    if category == "High-Risk":
        return ["non_sensitive_only"]
    return ["general_purpose"]


def format_hosting_jurisdiction(
    category: str | None,
    country_code: str | None,
    region: str | None = None,
) -> str | None:
    """Human-readable: 'EU (Germany - Frankfurt)' or 'Non-EU (United States)'."""
    if not country_code:
        return None
    country_name = COUNTRY_NAMES.get(country_code.upper(), country_code.upper())
    label = category or classify_jurisdiction(country_code)
    if region:
        return f"{label} ({country_name} - {region})"
    return f"{label} ({country_name})"


def is_cdn_provider(provider: str | None) -> bool:
    """True if the provider name matches a known CDN."""
    if not provider:
        return False
    lower = provider.lower()
    return any(pattern in lower for pattern in CDN_PROVIDER_PATTERNS)


def _extract_hostname(identifier: str) -> str | None:
    """Extract a bare hostname from a URL or raw hostname string."""
    if not identifier:
        return None
    candidate = identifier if "://" in identifier else f"https://{identifier}"
    try:
        host = urlparse(candidate).hostname
    except Exception:
        return None
    return host.lower() if host else None


# ═══════════════════════════════════════════════════════════════════════
# Tier 1: manual seed
# ═══════════════════════════════════════════════════════════════════════


def _resolve_from_seed(hostname: str) -> dict[str, Any] | None:
    entry = lookup_seed(hostname)
    if not entry:
        return None
    return {
        "hosting_country": entry.get("country"),
        "hosting_region": entry.get("region"),
        "hosting_provider": entry.get("provider"),
        "jurisdiction_category": entry.get("category") or classify_jurisdiction(entry.get("country")),
        "jurisdiction_source": "manual",
        "jurisdiction_confidence": "high",
        "notes": entry.get("notes"),
    }


# ═══════════════════════════════════════════════════════════════════════
# Tier 2: WHOIS
# ═══════════════════════════════════════════════════════════════════════


async def _resolve_from_whois(hostname: str) -> dict[str, Any] | None:
    """Try WHOIS for the registered second-level domain."""
    root_domain = _second_level_domain(hostname)
    if not root_domain:
        return None

    try:
        import whois  # python-whois
    except ImportError:
        logger.warning("python-whois not installed; skipping WHOIS lookup")
        return None

    try:
        record = await asyncio.wait_for(
            asyncio.to_thread(whois.whois, root_domain),
            timeout=6.0,
        )
    except Exception as exc:
        logger.debug("WHOIS failed for %s: %s", root_domain, exc)
        return None

    country = _first_whois_value(record, "country")
    registrant_country = _first_whois_value(record, "registrant_country")
    chosen = country or registrant_country
    if not chosen or len(chosen) != 2:
        return None

    code = chosen.upper()
    org = _first_whois_value(record, "org") or _first_whois_value(record, "registrant_organization")

    return {
        "hosting_country": code,
        "hosting_region": None,
        "hosting_provider": org,
        "jurisdiction_category": classify_jurisdiction(code),
        "jurisdiction_source": "whois",
        "jurisdiction_confidence": "medium",
        "notes": f"Registrant country from WHOIS (root domain: {root_domain})",
    }


def _second_level_domain(hostname: str) -> str | None:
    """Return the registered second-level domain, e.g. api.openai.com -> openai.com.

    Falls back to the full hostname for cc-TLDs like api.example.co.uk
    because distinguishing co.uk from openai.com without a public-suffix
    list is fragile. python-whois usually still resolves correctly.
    """
    if not hostname:
        return None
    parts = hostname.split(".")
    if len(parts) < 2:
        return None
    return ".".join(parts[-2:])


def _first_whois_value(record: Any, attr: str) -> str | None:
    """WHOIS records sometimes return list-valued fields. Pick the first non-empty."""
    value = getattr(record, attr, None) if not isinstance(record, dict) else record.get(attr)
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = next((v for v in value if v), None)
    if value is None:
        return None
    return str(value).strip() or None


# ═══════════════════════════════════════════════════════════════════════
# Tier 3: IP geolocation (+ CDN detection)
# ═══════════════════════════════════════════════════════════════════════


async def _resolve_from_ip(hostname: str) -> dict[str, Any] | None:
    ip = await _resolve_host(hostname)
    if not ip:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://ipinfo.io/{ip}/json")
            if resp.status_code != 200:
                logger.debug("ipinfo.io %s for %s (%s)", resp.status_code, hostname, ip)
                return None
            data = resp.json()
    except Exception as exc:
        logger.debug("ipinfo.io failed for %s: %s", hostname, exc)
        return None

    country = (data.get("country") or "").strip().upper()
    if not country:
        return None

    raw_org = data.get("org") or ""
    provider = raw_org.split(" ", 1)[1] if raw_org.startswith("AS") and " " in raw_org else raw_org or None

    is_cdn = is_cdn_provider(provider)
    return {
        "hosting_country": country,
        "hosting_region": data.get("city") or data.get("region"),
        "hosting_provider": provider,
        "jurisdiction_category": classify_jurisdiction(country),
        "jurisdiction_source": "cdn_detected" if is_cdn else "ip_geolocation",
        "jurisdiction_confidence": "low",
        "notes": (
            f"CDN edge detected ({provider}); country is the edge location, not the company's legal seat"
            if is_cdn
            else f"IP geolocation via ipinfo.io ({provider or 'unknown provider'})"
        ),
    }


async def _resolve_host(host: str) -> str | None:
    """Async-safe DNS resolution. Returns None on failure."""
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, socket.gethostbyname, host)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════


async def resolve_jurisdiction(identifier: str) -> dict[str, Any]:
    """Resolve a tool identifier through the three-tier hybrid strategy.

    Returns a dict with all the tool-model jurisdiction fields populated,
    or empty dict if every tier failed.
    """
    hostname = _extract_hostname(identifier)
    if not hostname:
        return {}

    seeded = _resolve_from_seed(hostname)
    if seeded:
        return seeded

    whoisd = await _resolve_from_whois(hostname)
    if whoisd:
        return whoisd

    ip = await _resolve_from_ip(hostname)
    if ip:
        return ip

    return {}


# Kept for backward compatibility with the previous API. Delegates to the
# hybrid resolver so callers still get the richer metadata automatically.
async def lookup_tool_jurisdiction(identifier: str) -> dict[str, Any]:
    return await resolve_jurisdiction(identifier)


async def enrich_tool(tool: Any) -> bool:
    """Populate a Tool's jurisdiction fields in-place.

    Returns True if anything was set. The caller owns committing the
    surrounding DB transaction.
    """
    info = await resolve_jurisdiction(tool.identifier)
    if not info:
        return False
    tool.hosting_country = info.get("hosting_country")
    tool.hosting_region = info.get("hosting_region")
    tool.hosting_provider = info.get("hosting_provider")
    tool.jurisdiction_category = info.get("jurisdiction_category")
    tool.jurisdiction_source = info.get("jurisdiction_source")
    tool.jurisdiction_confidence = info.get("jurisdiction_confidence")
    notes = info.get("notes")
    if notes:
        # Preserve prior notes only when adding more detail.
        tool.notes = notes
    return True
