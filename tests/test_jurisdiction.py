"""Tests for the jurisdiction service — classification, formatting, and compute_score integration."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.models.tool import Tool
from app.models.report import ExecutionReport
from app.services.scoring import compute_score, _get_eu_alternatives
from app.services.jurisdiction import (
    classify_jurisdiction,
    data_residency_risk,
    format_hosting_jurisdiction,
    is_cdn_provider,
    is_gdpr_compliant,
    recommended_for,
    resolve_jurisdiction,
    lookup_tool_jurisdiction,
    _resolve_from_seed,
    _second_level_domain,
    _extract_hostname,
)
from app.data.jurisdiction_seed import JURISDICTION_SEED, lookup_seed


TEST_DATABASE_URL = "sqlite+aiosqlite:///test_jurisdiction.db"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestClassifyJurisdiction:
    def test_eu_member(self):
        assert classify_jurisdiction("DE") == "EU"
        assert classify_jurisdiction("FR") == "EU"
        assert classify_jurisdiction("NL") == "EU"

    def test_eea_non_eu(self):
        assert classify_jurisdiction("NO") == "EU"
        assert classify_jurisdiction("IS") == "EU"

    def test_gdpr_adequate(self):
        assert classify_jurisdiction("GB") == "GDPR-adequate"
        assert classify_jurisdiction("CH") == "GDPR-adequate"
        assert classify_jurisdiction("JP") == "GDPR-adequate"

    def test_high_risk(self):
        assert classify_jurisdiction("CN") == "High-Risk"
        assert classify_jurisdiction("RU") == "High-Risk"

    def test_plain_non_eu(self):
        assert classify_jurisdiction("US") == "Non-EU"
        assert classify_jurisdiction("BR") == "Non-EU"

    def test_unknown_defaults_to_non_eu(self):
        assert classify_jurisdiction("ZZ") == "Non-EU"

    def test_none_or_empty(self):
        assert classify_jurisdiction(None) == "Non-EU"
        assert classify_jurisdiction("") == "Non-EU"

    def test_case_insensitive(self):
        assert classify_jurisdiction("de") == "EU"


class TestIsGdprCompliant:
    def test_eu_is_compliant(self):
        assert is_gdpr_compliant("EU") is True

    def test_adequate_is_compliant(self):
        assert is_gdpr_compliant("GDPR-adequate") is True

    def test_non_eu_is_not(self):
        assert is_gdpr_compliant("Non-EU") is False

    def test_high_risk_is_not(self):
        assert is_gdpr_compliant("High-Risk") is False

    def test_none_is_not(self):
        assert is_gdpr_compliant(None) is False


class TestDataResidencyRisk:
    def test_risk_mapping(self):
        assert data_residency_risk("EU") == "none"
        assert data_residency_risk("GDPR-adequate") == "low"
        assert data_residency_risk("Non-EU") == "medium"
        assert data_residency_risk("High-Risk") == "high"

    def test_unknown_is_medium(self):
        assert data_residency_risk(None) == "medium"
        assert data_residency_risk("") == "medium"

    def test_low_confidence_bumps_eu_to_low(self):
        """Low-confidence EU verdict should be downgraded — we're not sure it's really EU."""
        assert data_residency_risk("EU", confidence="low") == "low"

    def test_low_confidence_bumps_adequate_to_medium(self):
        assert data_residency_risk("GDPR-adequate", confidence="low") == "medium"

    def test_high_confidence_keeps_eu_at_none(self):
        assert data_residency_risk("EU", confidence="high") == "none"
        assert data_residency_risk("EU", confidence="medium") == "none"


class TestRecommendedFor:
    def test_eu_recommendations(self):
        tags = recommended_for("EU")
        assert "eu_companies" in tags
        assert "gdpr_strict_workflows" in tags
        assert "high_privacy_workflows" in tags

    def test_adequate_recommendations(self):
        tags = recommended_for("GDPR-adequate")
        assert "eu_companies" in tags
        assert "gdpr_flexible_workflows" in tags
        assert "gdpr_strict_workflows" not in tags

    def test_high_risk_restricted(self):
        assert recommended_for("High-Risk") == ["non_sensitive_only"]

    def test_non_eu_general(self):
        assert recommended_for("Non-EU") == ["general_purpose"]


class TestFormatHostingJurisdiction:
    def test_with_region(self):
        s = format_hosting_jurisdiction("EU", "DE", "Frankfurt")
        assert s == "EU (Germany - Frankfurt)"

    def test_without_region(self):
        s = format_hosting_jurisdiction("Non-EU", "US")
        assert s == "Non-EU (United States)"

    def test_derives_category_when_omitted(self):
        s = format_hosting_jurisdiction(None, "DE", "Berlin")
        assert s == "EU (Germany - Berlin)"

    def test_none_country_returns_none(self):
        assert format_hosting_jurisdiction("EU", None) is None

    def test_unknown_country_uses_code(self):
        s = format_hosting_jurisdiction("Non-EU", "ZZ")
        assert s == "Non-EU (ZZ)"


class TestLookupToolJurisdictionFallback:
    @pytest.mark.asyncio
    async def test_bad_url_returns_empty(self):
        result = await lookup_tool_jurisdiction("not-a-valid-url-at-all")
        # Might succeed if DNS resolves "not-a-valid-url-at-all" somehow — we
        # just care it doesn't raise.
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_empty_string_returns_empty(self):
        assert await lookup_tool_jurisdiction("") == {}


class TestComputeScoreJurisdictionFields:
    @pytest.mark.asyncio
    async def test_eu_tool_has_gdpr_fields(self, db):
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://eu-tool.example",
            category="LLM APIs",
            hosting_country="DE",
            hosting_region="Frankfurt",
            hosting_provider="Hetzner Online GmbH",
            jurisdiction_category="EU",
            report_count=0,
        )
        db.add(tool)
        await db.commit()

        resp = await compute_score(db, tool, "__global__")

        assert resp.hosting_jurisdiction == "EU (Germany - Frankfurt)"
        assert resp.gdpr_compliant is True
        assert resp.data_residency_risk == "none"
        assert "eu_companies" in resp.recommended_for

    @pytest.mark.asyncio
    async def test_us_tool_is_non_eu(self, db):
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://us-tool.example",
            category="LLM APIs",
            hosting_country="US",
            hosting_region="Virginia",
            hosting_provider="Amazon.com, Inc.",
            jurisdiction_category="Non-EU",
            report_count=0,
        )
        db.add(tool)
        await db.commit()

        resp = await compute_score(db, tool, "__global__")

        assert resp.hosting_jurisdiction == "Non-EU (United States - Virginia)"
        assert resp.gdpr_compliant is False
        assert resp.data_residency_risk == "medium"
        assert resp.recommended_for == ["general_purpose"]

    @pytest.mark.asyncio
    async def test_unknown_jurisdiction(self, db):
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://unknown.example",
            category="Other APIs",
            report_count=0,
        )
        db.add(tool)
        await db.commit()

        resp = await compute_score(db, tool, "__global__")

        assert resp.hosting_jurisdiction is None
        assert resp.gdpr_compliant is False
        assert resp.data_residency_risk == "medium"
        assert resp.eu_alternatives == []


class TestEuAlternatives:
    @pytest.mark.asyncio
    async def test_returns_eu_peers_in_same_category(self, db):
        # Primary US-hosted LLM
        primary = Tool(
            id=uuid.uuid4(),
            identifier="https://primary-us-llm.example",
            category="LLM APIs",
            jurisdiction_category="Non-EU",
            hosting_country="US",
            report_count=100,
        )
        # Two EU peers in same category
        eu1 = Tool(
            id=uuid.uuid4(),
            identifier="https://eu-llm-1.example",
            category="LLM APIs",
            jurisdiction_category="EU",
            hosting_country="DE",
            report_count=80,
        )
        eu2 = Tool(
            id=uuid.uuid4(),
            identifier="https://eu-llm-2.example",
            category="LLM APIs",
            jurisdiction_category="EU",
            hosting_country="FR",
            report_count=60,
        )
        # GDPR-adequate (UK) peer — should only appear when gdpr_required=True
        uk = Tool(
            id=uuid.uuid4(),
            identifier="https://uk-llm.example",
            category="LLM APIs",
            jurisdiction_category="GDPR-adequate",
            hosting_country="GB",
            report_count=70,
        )
        # Different category — should never appear
        payments = Tool(
            id=uuid.uuid4(),
            identifier="https://eu-payments.example",
            category="Payment APIs",
            jurisdiction_category="EU",
            hosting_country="NL",
            report_count=90,
        )
        db.add_all([primary, eu1, eu2, uk, payments])
        await db.commit()

        # eu_only=True → only EU peers (no UK)
        alts = await _get_eu_alternatives(db, primary, gdpr_required=False)
        idents = [a.tool for a in alts]
        assert "https://eu-llm-1.example" in idents
        assert "https://eu-llm-2.example" in idents
        assert "https://uk-llm.example" not in idents
        assert "https://eu-payments.example" not in idents

    @pytest.mark.asyncio
    async def test_gdpr_required_includes_adequate(self, db):
        primary = Tool(
            id=uuid.uuid4(),
            identifier="https://primary.example",
            category="Email APIs",
            jurisdiction_category="Non-EU",
            hosting_country="US",
            report_count=100,
        )
        uk = Tool(
            id=uuid.uuid4(),
            identifier="https://uk-email.example",
            category="Email APIs",
            jurisdiction_category="GDPR-adequate",
            hosting_country="GB",
            report_count=50,
        )
        db.add_all([primary, uk])
        await db.commit()

        alts = await _get_eu_alternatives(db, primary, gdpr_required=True)
        assert any(a.tool == "https://uk-email.example" for a in alts)

    @pytest.mark.asyncio
    async def test_excludes_low_report_count(self, db):
        primary = Tool(
            id=uuid.uuid4(),
            identifier="https://primary.example",
            category="LLM APIs",
            jurisdiction_category="Non-EU",
            hosting_country="US",
            report_count=100,
        )
        lonely_eu = Tool(
            id=uuid.uuid4(),
            identifier="https://lonely-eu.example",
            category="LLM APIs",
            jurisdiction_category="EU",
            hosting_country="DE",
            report_count=2,  # below threshold of 5
        )
        db.add_all([primary, lonely_eu])
        await db.commit()

        alts = await _get_eu_alternatives(db, primary, gdpr_required=False)
        assert alts == []

    @pytest.mark.asyncio
    async def test_compute_score_surfaces_eu_alternatives(self, db):
        primary = Tool(
            id=uuid.uuid4(),
            identifier="https://primary.example",
            category="LLM APIs",
            jurisdiction_category="Non-EU",
            hosting_country="US",
            report_count=100,
        )
        eu_peer = Tool(
            id=uuid.uuid4(),
            identifier="https://eu-peer.example",
            category="LLM APIs",
            jurisdiction_category="EU",
            hosting_country="DE",
            report_count=80,
        )
        db.add_all([primary, eu_peer])
        await db.commit()

        # With eu_only, eu_alternatives should be populated
        resp_eu = await compute_score(db, primary, "__global__", eu_only=True)
        assert len(resp_eu.eu_alternatives) == 1
        assert resp_eu.eu_alternatives[0].tool == "https://eu-peer.example"

        # Without the flag, eu_alternatives should be empty
        resp_plain = await compute_score(db, primary, "__global__")
        assert resp_plain.eu_alternatives == []


class TestExtractHostname:
    def test_full_url(self):
        assert _extract_hostname("https://api.openai.com/v1/chat/completions") == "api.openai.com"

    def test_bare_hostname(self):
        assert _extract_hostname("api.openai.com") == "api.openai.com"

    def test_lowercases(self):
        assert _extract_hostname("https://API.OPENAI.COM/foo") == "api.openai.com"

    def test_empty_returns_none(self):
        assert _extract_hostname("") is None
        assert _extract_hostname(None) is None


class TestSecondLevelDomain:
    def test_three_part(self):
        assert _second_level_domain("api.openai.com") == "openai.com"

    def test_four_part(self):
        # Without a PSL we collapse everything to the last two labels.
        # This is imperfect for co.uk but WHOIS usually still resolves.
        assert _second_level_domain("api.graph.facebook.com") == "facebook.com"

    def test_already_root(self):
        assert _second_level_domain("openai.com") == "openai.com"

    def test_single_label(self):
        assert _second_level_domain("localhost") is None


class TestIsCdnProvider:
    def test_cloudflare(self):
        assert is_cdn_provider("Cloudflare, Inc.") is True
        assert is_cdn_provider("cloudflarenet") is True

    def test_fastly(self):
        assert is_cdn_provider("Fastly, Inc.") is True

    def test_akamai(self):
        assert is_cdn_provider("Akamai Technologies") is True

    def test_non_cdn(self):
        assert is_cdn_provider("Hetzner Online GmbH") is False
        assert is_cdn_provider("OpenAI, Inc.") is False

    def test_empty(self):
        assert is_cdn_provider(None) is False
        assert is_cdn_provider("") is False

    def test_aws_and_google_not_flagged(self):
        """We deliberately don't flag AWS/Google as CDNs — they're hosts for real services."""
        assert is_cdn_provider("Amazon.com, Inc.") is False
        assert is_cdn_provider("Google LLC") is False


class TestJurisdictionSeed:
    def test_seed_has_critical_entries(self):
        # Sanity check: if these disappear, production data is wrong
        assert "api.openai.com" in JURISDICTION_SEED
        assert "api.anthropic.com" in JURISDICTION_SEED
        assert "api.stripe.com" in JURISDICTION_SEED
        assert "api.mistral.ai" in JURISDICTION_SEED

    def test_openai_is_us_non_eu(self):
        entry = lookup_seed("api.openai.com")
        assert entry is not None
        assert entry["country"] == "US"
        assert entry["category"] == "Non-EU"

    def test_mistral_is_eu(self):
        entry = lookup_seed("api.mistral.ai")
        assert entry is not None
        assert entry["country"] == "FR"
        assert entry["category"] == "EU"

    def test_deepseek_is_high_risk(self):
        entry = lookup_seed("api.deepseek.com")
        assert entry is not None
        assert entry["category"] == "High-Risk"

    def test_case_insensitive(self):
        assert lookup_seed("API.OPENAI.COM") is not None

    def test_missing_returns_none(self):
        assert lookup_seed("api.nothing-here-42.example") is None

    def test_www_prefix_stripped(self):
        # Register bare, query with www. — should still match
        assert lookup_seed("www.api.openai.com") is not None


class TestResolveFromSeed:
    def test_converts_seed_to_resolver_dict(self):
        result = _resolve_from_seed("api.openai.com")
        assert result is not None
        assert result["hosting_country"] == "US"
        assert result["jurisdiction_category"] == "Non-EU"
        assert result["jurisdiction_source"] == "manual"
        assert result["jurisdiction_confidence"] == "high"
        assert result["notes"] is not None

    def test_returns_none_for_unseeded(self):
        assert _resolve_from_seed("api.unknown-42.example") is None


class TestResolveJurisdictionTiers:
    @pytest.mark.asyncio
    async def test_seed_wins_over_whois_and_ip(self):
        """When a tool is in the seed, WHOIS and IP lookups should never fire."""
        with patch("app.services.jurisdiction._resolve_from_whois", new=AsyncMock(return_value={"should": "not be called"})) as whois_mock, \
             patch("app.services.jurisdiction._resolve_from_ip", new=AsyncMock(return_value={"should": "not be called"})) as ip_mock:
            result = await resolve_jurisdiction("https://api.openai.com/v1/chat/completions")

        assert result["jurisdiction_source"] == "manual"
        assert result["hosting_country"] == "US"
        whois_mock.assert_not_called()
        ip_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_whois_used_when_seed_misses(self):
        """When no seed exists, WHOIS should be tried next."""
        fake_whois = {
            "hosting_country": "DE",
            "hosting_region": None,
            "hosting_provider": "Example GmbH",
            "jurisdiction_category": "EU",
            "jurisdiction_source": "whois",
            "jurisdiction_confidence": "medium",
            "notes": "Registrant country from WHOIS",
        }
        with patch("app.services.jurisdiction._resolve_from_whois", new=AsyncMock(return_value=fake_whois)), \
             patch("app.services.jurisdiction._resolve_from_ip", new=AsyncMock(return_value=None)) as ip_mock:
            result = await resolve_jurisdiction("https://api.unseeded-example.test/v1")

        assert result["jurisdiction_source"] == "whois"
        assert result["jurisdiction_confidence"] == "medium"
        ip_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_ip_fallback_when_whois_fails(self):
        fake_ip = {
            "hosting_country": "US",
            "hosting_region": "Virginia",
            "hosting_provider": "Amazon.com, Inc.",
            "jurisdiction_category": "Non-EU",
            "jurisdiction_source": "ip_geolocation",
            "jurisdiction_confidence": "low",
            "notes": "IP geolocation via ipinfo.io",
        }
        with patch("app.services.jurisdiction._resolve_from_whois", new=AsyncMock(return_value=None)), \
             patch("app.services.jurisdiction._resolve_from_ip", new=AsyncMock(return_value=fake_ip)):
            result = await resolve_jurisdiction("https://api.unseeded-example.test/v1")

        assert result["jurisdiction_source"] == "ip_geolocation"
        assert result["jurisdiction_confidence"] == "low"

    @pytest.mark.asyncio
    async def test_cdn_detected_flag(self):
        fake_ip = {
            "hosting_country": "DE",
            "hosting_region": "Frankfurt",
            "hosting_provider": "Cloudflare, Inc.",
            "jurisdiction_category": "EU",
            "jurisdiction_source": "cdn_detected",
            "jurisdiction_confidence": "low",
            "notes": "CDN edge detected",
        }
        with patch("app.services.jurisdiction._resolve_from_whois", new=AsyncMock(return_value=None)), \
             patch("app.services.jurisdiction._resolve_from_ip", new=AsyncMock(return_value=fake_ip)):
            result = await resolve_jurisdiction("https://api.some-cdn-fronted.test/v1")

        assert result["jurisdiction_source"] == "cdn_detected"
        assert result["jurisdiction_confidence"] == "low"

    @pytest.mark.asyncio
    async def test_all_tiers_fail_returns_empty(self):
        with patch("app.services.jurisdiction._resolve_from_whois", new=AsyncMock(return_value=None)), \
             patch("app.services.jurisdiction._resolve_from_ip", new=AsyncMock(return_value=None)):
            result = await resolve_jurisdiction("https://api.unseeded-example.test/v1")

        assert result == {}


class TestComputeScoreExposesConfidence:
    @pytest.mark.asyncio
    async def test_manual_source_surfaces_in_response(self, db):
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://api.openai.com/v1/chat/completions",
            category="LLM APIs",
            hosting_country="US",
            hosting_region="San Francisco, CA",
            hosting_provider="OpenAI Inc.",
            jurisdiction_category="Non-EU",
            jurisdiction_source="manual",
            jurisdiction_confidence="high",
            notes="OpenAI OpCo, LLC (Delaware).",
            report_count=0,
        )
        db.add(tool)
        await db.commit()

        resp = await compute_score(db, tool, "__global__")

        assert resp.jurisdiction_source == "manual"
        assert resp.jurisdiction_confidence == "high"
        assert resp.jurisdiction_notes == "OpenAI OpCo, LLC (Delaware)."
        assert resp.hosting_jurisdiction == "Non-EU (United States - San Francisco, CA)"

    @pytest.mark.asyncio
    async def test_cdn_detected_has_bumped_residency_risk(self, db):
        """A cdn_detected verdict claiming 'EU' should still carry low-confidence risk."""
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://api.cdn-fronted.test",
            category="LLM APIs",
            hosting_country="DE",
            hosting_region="Frankfurt",
            hosting_provider="Cloudflare, Inc.",
            jurisdiction_category="EU",
            jurisdiction_source="cdn_detected",
            jurisdiction_confidence="low",
            report_count=0,
        )
        db.add(tool)
        await db.commit()

        resp = await compute_score(db, tool, "__global__")

        # EU + high confidence would be 'none', but with low confidence it gets bumped
        assert resp.data_residency_risk == "low"
        assert resp.jurisdiction_confidence == "low"
        assert resp.jurisdiction_source == "cdn_detected"
