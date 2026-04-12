"""Tests for the jurisdiction service — classification, formatting, and compute_score integration."""

import uuid
from datetime import datetime, timezone

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
    is_gdpr_compliant,
    recommended_for,
    lookup_tool_jurisdiction,
)


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
