"""Jurisdiction-aware tool metadata — country, provider, GDPR classification.

Resolves a tool identifier (URL) to the country its IP lives in, groups
that country into a GDPR bucket (EU / GDPR-adequate / Non-EU / High-Risk),
and derives downstream flags used by the /assess endpoint:

    hosting_jurisdiction : 'EU (Germany - Frankfurt)'
    gdpr_compliant       : bool
    data_residency_risk  : 'none' | 'low' | 'medium' | 'high'
    recommended_for      : ['eu_companies', 'gdpr_strict_workflows', ...]

Uses ipinfo.io as the geo backend (free tier, HTTPS, no auth for low volumes).
All lookups are best-effort — a failure leaves the tool's jurisdiction fields
as NULL, which downstream code treats the same as 'Non-EU / medium risk'.
"""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("nemoflow.jurisdiction")

JurisdictionCategory = Literal["EU", "Non-EU", "GDPR-adequate", "High-Risk"]
DataResidencyRisk = Literal["none", "low", "medium", "high"]

# EU + EEA. Jurisdictions that fall under GDPR directly.
EU_COUNTRIES: frozenset[str] = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
    # EEA
    "IS", "LI", "NO",
})

# Jurisdictions covered by an EU Commission adequacy decision (as of 2024).
GDPR_ADEQUATE_COUNTRIES: frozenset[str] = frozenset({
    "AD", "AR", "CA", "FO", "GG", "IL", "IM", "JP", "JE", "NZ", "KR",
    "CH", "GB", "UY",
})

# Jurisdictions with active mass-surveillance or no meaningful privacy framework.
HIGH_RISK_COUNTRIES: frozenset[str] = frozenset({
    "CN", "RU", "IR", "KP", "BY", "SY",
})

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


def data_residency_risk(category: str | None) -> DataResidencyRisk:
    """Risk that routing data through this jurisdiction creates a GDPR problem."""
    return {
        "EU": "none",
        "GDPR-adequate": "low",
        "Non-EU": "medium",
        "High-Risk": "high",
    }.get(category or "", "medium")


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


async def lookup_tool_jurisdiction(identifier: str) -> dict[str, Any]:
    """Resolve a tool URL to hosting country/region/provider via DNS + ipinfo.io.

    Returns a dict with hosting_country, hosting_region, hosting_provider,
    and jurisdiction_category. Returns an empty dict on any failure so callers
    can treat enrichment as purely additive.
    """
    try:
        parsed = urlparse(identifier if "://" in identifier else f"https://{identifier}")
        host = parsed.hostname
        if not host:
            return {}

        ip = await _resolve_host(host)
        if not ip:
            return {}

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://ipinfo.io/{ip}/json")
            if resp.status_code != 200:
                logger.warning(
                    "ipinfo.io returned %s for %s (%s)", resp.status_code, identifier, ip,
                )
                return {}
            data = resp.json()

        country = (data.get("country") or "").strip().upper()
        if not country:
            return {}

        # ipinfo 'org' is like 'AS24940 Hetzner Online GmbH'. Strip the ASN prefix.
        raw_org = data.get("org") or ""
        provider = raw_org.split(" ", 1)[1] if raw_org.startswith("AS") and " " in raw_org else raw_org

        return {
            "hosting_country": country,
            "hosting_region": data.get("city") or data.get("region"),
            "hosting_provider": provider or None,
            "jurisdiction_category": classify_jurisdiction(country),
        }
    except Exception as exc:
        logger.warning("Jurisdiction lookup failed for %s: %s", identifier, exc)
        return {}


async def _resolve_host(host: str) -> str | None:
    """Async-safe DNS resolution. Returns None on failure."""
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, socket.gethostbyname, host)
    except Exception:
        return None


async def enrich_tool(tool: Any) -> bool:
    """Populate a Tool's jurisdiction fields in-place. Returns True if anything was set.

    Caller is responsible for committing the surrounding DB transaction.
    """
    info = await lookup_tool_jurisdiction(tool.identifier)
    if not info:
        return False
    tool.hosting_country = info.get("hosting_country")
    tool.hosting_region = info.get("hosting_region")
    tool.hosting_provider = info.get("hosting_provider")
    tool.jurisdiction_category = info.get("jurisdiction_category")
    return True
