"""Tests for outbound webhook dispatch — SSRF revalidation, redirect policy,
shared failure counter, and auto-deactivation.

The production ``_deliver`` function imports ``async_session`` lazily from
``app.db.session`` inside the function body. Each test monkeypatches that
attribute to a SQLite-backed session factory so the webhook_dispatch module
reads/writes the in-memory test DB without touching production Postgres.

``is_public_url`` is monkeypatched directly on the webhook_dispatch module
for the rebinding scenario — that's cleaner than mocking the underlying
``socket.getaddrinfo`` plumbing and it's what an agent developer would
actually reach for when stubbing SSRF outcomes in integration tests.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.models.api_key import ApiKey
from app.models.webhook import Webhook
from app.services import webhook_dispatch


TEST_DATABASE_URL = "sqlite+aiosqlite:///test_webhook_dispatch.db"


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_factory(monkeypatch):
    """Create a SQLite engine + session factory, patch app.db.session to use it.

    The ``raising=False`` on the monkeypatch lets us set the attribute even
    if the import has been lazy-deferred somewhere in the module chain.
    """
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(
        "app.db.session.async_session", session_factory, raising=False
    )

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _create_webhook(
    session_factory,
    *,
    url: str = "https://example.com/hook",
    failure_count: int = 0,
) -> uuid.UUID:
    async with session_factory() as db:
        api_key = ApiKey(
            key_hash="test_hash_" + uuid.uuid4().hex,
            key_prefix="nf_test",
            tier="pro",
            daily_limit=10000,
        )
        db.add(api_key)
        await db.flush()

        wh = Webhook(
            id=uuid.uuid4(),
            api_key_id=api_key.id,
            url=url,
            event="score.change",
            tool_identifier=None,
            threshold=5,
            secret="test_secret_" + uuid.uuid4().hex,
            is_active=True,
            failure_count=failure_count,
        )
        db.add(wh)
        await db.commit()
        await db.refresh(wh)
        return wh.id


async def _get_webhook(session_factory, webhook_id: uuid.UUID) -> Webhook:
    async with session_factory() as db:
        result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
        return result.scalar_one()


@pytest.fixture
def payload():
    return {
        "event": "score.change",
        "tool_identifier": "https://api.stripe.com/v1/charges",
        "old_score": 80.0,
        "new_score": 85.0,
        "delta": 5.0,
        "timestamp": "2026-04-15T10:00:00Z",
    }


def _mock_httpx_client(monkeypatch, *, status_code: int = 200):
    """Install a mock httpx client and return the mock + its .post AsyncMock.

    Returning both lets tests inspect the mock AND swap its return value
    or side_effect without digging into ``webhook_dispatch._client``.
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(webhook_dispatch, "_get_client", lambda: mock_client)
    return mock_client


# ──────────────────────────────────────────────────────────────────────────
# SSRF revalidation at delivery time
# ──────────────────────────────────────────────────────────────────────────


class TestSSRFRevalidation:
    @pytest.mark.asyncio
    async def test_literal_internal_ip_blocked_at_delivery(
        self, db_factory, payload, monkeypatch
    ):
        """A webhook whose URL points at a literal RFC1918 address is
        blocked before any HTTP call, even if registration's URL validator
        never ran (e.g. schema migration from an older, laxer era)."""
        webhook_id = await _create_webhook(db_factory, url="http://10.0.0.5/hook")
        mock_client = _mock_httpx_client(monkeypatch)

        await webhook_dispatch._deliver(
            webhook_id, "http://10.0.0.5/hook", "secret", payload
        )

        mock_client.post.assert_not_called()
        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 1
        assert wh.is_active is True

    @pytest.mark.asyncio
    async def test_cloud_metadata_url_blocked(
        self, db_factory, payload, monkeypatch
    ):
        """169.254.169.254 is the AWS/GCP instance-metadata endpoint and
        the worst possible SSRF target. Must be rejected unconditionally."""
        url = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
        webhook_id = await _create_webhook(db_factory, url=url)
        mock_client = _mock_httpx_client(monkeypatch)

        await webhook_dispatch._deliver(webhook_id, url, "secret", payload)

        mock_client.post.assert_not_called()
        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 1

    @pytest.mark.asyncio
    async def test_dns_rebinding_simulated_via_mocked_is_public_url(
        self, db_factory, payload, monkeypatch
    ):
        """Happy-path URL at registration time flips to 'internal' at
        delivery — simulated by stubbing ``is_public_url`` to return False.
        This is the actual DNS rebinding attack shape: a hostname that was
        public when the webhook was created but now points inside."""
        webhook_id = await _create_webhook(
            db_factory, url="https://attacker-rebound.example.com/hook"
        )
        monkeypatch.setattr(webhook_dispatch, "is_public_url", lambda url: False)
        mock_client = _mock_httpx_client(monkeypatch)

        await webhook_dispatch._deliver(
            webhook_id,
            "https://attacker-rebound.example.com/hook",
            "secret",
            payload,
        )

        mock_client.post.assert_not_called()
        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 1

    @pytest.mark.asyncio
    async def test_localhost_hostname_blocked(
        self, db_factory, payload, monkeypatch
    ):
        """``localhost`` is in the _BLOCKED_HOSTNAMES set, rejected
        regardless of the actual DNS resolution."""
        webhook_id = await _create_webhook(db_factory, url="http://localhost/hook")
        mock_client = _mock_httpx_client(monkeypatch)

        await webhook_dispatch._deliver(
            webhook_id, "http://localhost/hook", "secret", payload
        )

        mock_client.post.assert_not_called()
        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 1


# ──────────────────────────────────────────────────────────────────────────
# Happy path + httpx call shape
# ──────────────────────────────────────────────────────────────────────────


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_public_url_delivers_and_resets_failure_count(
        self, db_factory, payload, monkeypatch
    ):
        webhook_id = await _create_webhook(
            db_factory, url="https://example.com/hook", failure_count=3,
        )
        monkeypatch.setattr(webhook_dispatch, "is_public_url", lambda url: True)
        mock_client = _mock_httpx_client(monkeypatch, status_code=200)

        await webhook_dispatch._deliver(
            webhook_id, "https://example.com/hook", "secret", payload
        )

        mock_client.post.assert_called_once()
        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 0
        assert wh.last_triggered_at is not None

    @pytest.mark.asyncio
    async def test_follow_redirects_false_passed_to_httpx(
        self, db_factory, payload, monkeypatch
    ):
        """Defense-in-depth: we pin ``follow_redirects=False`` explicitly
        so a silent upstream default flip can't enable redirect-chain SSRF
        (attacker.com → 302 → http://169.254.169.254/...)."""
        webhook_id = await _create_webhook(
            db_factory, url="https://example.com/hook"
        )
        monkeypatch.setattr(webhook_dispatch, "is_public_url", lambda url: True)
        mock_client = _mock_httpx_client(monkeypatch)

        await webhook_dispatch._deliver(
            webhook_id, "https://example.com/hook", "secret", payload
        )

        _args, kwargs = mock_client.post.call_args
        assert kwargs.get("follow_redirects") is False

    @pytest.mark.asyncio
    async def test_5xx_response_counts_as_failure(
        self, db_factory, payload, monkeypatch
    ):
        webhook_id = await _create_webhook(
            db_factory, url="https://example.com/hook"
        )
        monkeypatch.setattr(webhook_dispatch, "is_public_url", lambda url: True)
        _mock_httpx_client(monkeypatch, status_code=500)

        await webhook_dispatch._deliver(
            webhook_id, "https://example.com/hook", "secret", payload
        )

        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 1
        assert wh.is_active is True

    @pytest.mark.asyncio
    async def test_network_exception_counts_as_failure(
        self, db_factory, payload, monkeypatch
    ):
        """httpx raises (connect timeout, TLS error, etc.) → caught and
        recorded as a failure, never leaks out of ``_deliver``."""
        import httpx

        webhook_id = await _create_webhook(
            db_factory, url="https://example.com/hook"
        )
        monkeypatch.setattr(webhook_dispatch, "is_public_url", lambda url: True)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("simulated connect failure")
        )
        monkeypatch.setattr(webhook_dispatch, "_get_client", lambda: mock_client)

        # Should NOT raise
        await webhook_dispatch._deliver(
            webhook_id, "https://example.com/hook", "secret", payload
        )

        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 1


# ──────────────────────────────────────────────────────────────────────────
# Auto-deactivation — the 10-strike rule applies across all failure types
# ──────────────────────────────────────────────────────────────────────────


class TestAutoDeactivation:
    @pytest.mark.asyncio
    async def test_ten_consecutive_ssrf_blocks_deactivate_webhook(
        self, db_factory, payload, monkeypatch
    ):
        """SSRF-blocked deliveries flow through the same counter as normal
        failures, so a webhook whose domain keeps resolving to internal
        IPs gets auto-disabled after 10 tries."""
        webhook_id = await _create_webhook(db_factory, url="http://10.0.0.5/hook")
        _mock_httpx_client(monkeypatch)

        for _ in range(10):
            await webhook_dispatch._deliver(
                webhook_id, "http://10.0.0.5/hook", "secret", payload
            )

        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 10
        assert wh.is_active is False

    @pytest.mark.asyncio
    async def test_nine_failures_then_success_clears_count(
        self, db_factory, payload, monkeypatch
    ):
        """Failure counter is SUCCESS-resetting: 9 failures + 1 success
        → 0, not 9. The 10-strike auto-deactivate only fires on a streak
        of consecutive failures."""
        webhook_id = await _create_webhook(
            db_factory, url="https://example.com/hook", failure_count=9,
        )
        monkeypatch.setattr(webhook_dispatch, "is_public_url", lambda url: True)
        _mock_httpx_client(monkeypatch, status_code=200)

        await webhook_dispatch._deliver(
            webhook_id, "https://example.com/hook", "secret", payload
        )

        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 0
        assert wh.is_active is True

    @pytest.mark.asyncio
    async def test_deactivation_triggers_exactly_at_ten(
        self, db_factory, payload, monkeypatch
    ):
        """Boundary check: starting at failure_count=9, a single additional
        failure should flip is_active to False in the same atomic UPDATE."""
        webhook_id = await _create_webhook(
            db_factory, url="http://10.0.0.5/hook", failure_count=9,
        )
        _mock_httpx_client(monkeypatch)

        await webhook_dispatch._deliver(
            webhook_id, "http://10.0.0.5/hook", "secret", payload
        )

        wh = await _get_webhook(db_factory, webhook_id)
        assert wh.failure_count == 10
        assert wh.is_active is False
