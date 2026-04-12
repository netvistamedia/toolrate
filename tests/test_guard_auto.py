"""Unit tests for toolrate.guard — focused on the fallbacks="auto" mode."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# The SDK lives under sdks/python and isn't pip-installed in CI, so make its
# package directory importable before we import from it.
_SDK_PATH = str(Path(__file__).resolve().parent.parent / "sdks" / "python")
if _SDK_PATH not in sys.path:
    sys.path.insert(0, _SDK_PATH)

from toolrate.guard import guard, _resolve_auto_fallbacks  # noqa: E402


class FakeClient:
    """Minimal ToolRate client stand-in that records calls and returns scripted responses."""

    def __init__(
        self,
        assessments: dict[str, dict[str, Any]] | None = None,
        fallback_chains: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.assessments = assessments or {}
        self.fallback_chains = fallback_chains or {}
        self.reports: list[dict[str, Any]] = []
        self.assess_calls: list[str] = []
        self.chain_calls: list[str] = []

    def assess(self, tool_identifier: str, context: str = "") -> dict[str, Any]:
        self.assess_calls.append(tool_identifier)
        return self.assessments.get(tool_identifier, {"reliability_score": 100})

    def report(self, tool_identifier: str, **kwargs: Any) -> dict[str, Any]:
        self.reports.append({"tool_identifier": tool_identifier, **kwargs})
        return {"status": "ok"}

    def discover_fallback_chain(self, tool_identifier: str, limit: int = 5) -> dict[str, Any]:
        self.chain_calls.append(tool_identifier)
        return self.fallback_chains.get(tool_identifier, {"fallback_chain": []})


class TestResolveAutoFallbacks:
    def test_uses_top_alternatives_from_assessment(self):
        client = FakeClient()
        assessment = {
            "top_alternatives": [
                {"tool": "https://api.anthropic.com/v1/messages"},
                {"tool": "https://api.groq.com/openai/v1/chat/completions"},
            ]
        }
        resolvers = {
            "https://api.anthropic.com/v1/messages": lambda: "anthropic-result",
            "https://api.groq.com/openai/v1/chat/completions": lambda: "groq-result",
        }

        fallbacks = _resolve_auto_fallbacks(
            client, "https://api.openai.com/v1/chat/completions",
            assessment, resolvers, max_n=3,
        )

        assert [ident for ident, _ in fallbacks] == [
            "https://api.anthropic.com/v1/messages",
            "https://api.groq.com/openai/v1/chat/completions",
        ]
        assert client.chain_calls == []  # no extra API call needed

    def test_falls_back_to_discover_chain(self):
        client = FakeClient(fallback_chains={
            "https://api.openai.com/v1/chat/completions": {
                "fallback_chain": [{"fallback_tool": "https://api.anthropic.com/v1/messages"}]
            }
        })
        resolvers = {
            "https://api.anthropic.com/v1/messages": lambda: "anthropic-result",
        }

        fallbacks = _resolve_auto_fallbacks(
            client, "https://api.openai.com/v1/chat/completions",
            {"top_alternatives": []}, resolvers, max_n=3,
        )

        assert len(fallbacks) == 1
        assert fallbacks[0][0] == "https://api.anthropic.com/v1/messages"
        assert client.chain_calls == ["https://api.openai.com/v1/chat/completions"]

    def test_skips_candidates_without_resolvers(self):
        assessment = {
            "top_alternatives": [
                {"tool": "https://unknown.example/api"},
                {"tool": "https://api.anthropic.com/v1/messages"},
            ]
        }
        resolvers = {
            "https://api.anthropic.com/v1/messages": lambda: "ok",
        }

        fallbacks = _resolve_auto_fallbacks(
            FakeClient(), "https://api.openai.com/v1/chat/completions",
            assessment, resolvers, max_n=3,
        )

        assert len(fallbacks) == 1
        assert fallbacks[0][0] == "https://api.anthropic.com/v1/messages"

    def test_respects_max_n(self):
        assessment = {
            "top_alternatives": [
                {"tool": "https://a.example"}, {"tool": "https://b.example"},
                {"tool": "https://c.example"}, {"tool": "https://d.example"},
            ]
        }
        resolvers = {
            "https://a.example": lambda: 1,
            "https://b.example": lambda: 2,
            "https://c.example": lambda: 3,
            "https://d.example": lambda: 4,
        }

        fallbacks = _resolve_auto_fallbacks(
            FakeClient(), "https://primary.example",
            assessment, resolvers, max_n=2,
        )

        assert len(fallbacks) == 2

    def test_excludes_primary_from_auto(self):
        """Primary tool should never appear in its own fallback list."""
        assessment = {
            "top_alternatives": [
                {"tool": "https://api.openai.com/v1/chat/completions"},
                {"tool": "https://api.anthropic.com/v1/messages"},
            ]
        }
        resolvers = {
            "https://api.openai.com/v1/chat/completions": lambda: "primary",
            "https://api.anthropic.com/v1/messages": lambda: "secondary",
        }

        fallbacks = _resolve_auto_fallbacks(
            FakeClient(), "https://api.openai.com/v1/chat/completions",
            assessment, resolvers, max_n=3,
        )

        assert len(fallbacks) == 1
        assert fallbacks[0][0] == "https://api.anthropic.com/v1/messages"

    def test_empty_resolvers_returns_nothing(self):
        assessment = {"top_alternatives": [{"tool": "https://a.example"}]}
        fallbacks = _resolve_auto_fallbacks(
            FakeClient(), "https://primary.example", assessment, {}, max_n=3,
        )
        assert fallbacks == []


class TestGuardAutoFallback:
    def test_primary_succeeds_does_not_invoke_fallback(self):
        client = FakeClient(assessments={
            "https://primary.example": {
                "reliability_score": 100,
                "top_alternatives": [{"tool": "https://backup.example"}],
            },
        })
        backup_called = []
        resolvers = {"https://backup.example": lambda: backup_called.append(True)}

        result = guard(
            client, "https://primary.example", lambda: "primary-ok",
            fallbacks="auto", resolvers=resolvers,
        )

        assert result == "primary-ok"
        assert backup_called == []
        # Exactly one report (for primary success)
        assert len(client.reports) == 1
        assert client.reports[0]["success"] is True

    def test_primary_fails_falls_back_to_auto(self):
        client = FakeClient(assessments={
            "https://primary.example": {
                "reliability_score": 100,
                "top_alternatives": [{"tool": "https://backup.example"}],
            },
            "https://backup.example": {"reliability_score": 100},
        })

        def broken():
            raise RuntimeError("boom")

        resolvers = {"https://backup.example": lambda: "backup-ok"}

        result = guard(
            client, "https://primary.example", broken,
            fallbacks="auto", resolvers=resolvers,
        )

        assert result == "backup-ok"
        # Primary failure + backup success
        assert len(client.reports) == 2
        assert client.reports[0]["tool_identifier"] == "https://primary.example"
        assert client.reports[0]["success"] is False
        assert client.reports[1]["tool_identifier"] == "https://backup.example"
        assert client.reports[1]["success"] is True
        # Backup should know it was attempt 2 with primary as previous_tool
        assert client.reports[1]["attempt_number"] == 2
        assert client.reports[1]["previous_tool"] == "https://primary.example"

    def test_auto_all_fail_raises_last_error(self):
        client = FakeClient(assessments={
            "https://primary.example": {
                "reliability_score": 100,
                "top_alternatives": [{"tool": "https://backup.example"}],
            },
            "https://backup.example": {"reliability_score": 100},
        })

        def broken_primary():
            raise RuntimeError("primary boom")

        def broken_backup():
            raise RuntimeError("backup boom")

        with pytest.raises(RuntimeError, match="backup boom"):
            guard(
                client, "https://primary.example", broken_primary,
                fallbacks="auto",
                resolvers={"https://backup.example": broken_backup},
            )

    def test_auto_without_resolvers_raises_original_error(self):
        """fallbacks='auto' with no matching resolvers behaves like no fallbacks."""
        client = FakeClient(assessments={
            "https://primary.example": {
                "reliability_score": 100,
                "top_alternatives": [{"tool": "https://backup.example"}],
            },
        })

        def broken():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            guard(
                client, "https://primary.example", broken,
                fallbacks="auto", resolvers={},
            )

    def test_explicit_fallbacks_still_work(self):
        """Regression: the existing explicit-fallbacks path still functions."""
        client = FakeClient(assessments={
            "https://a.example": {"reliability_score": 100},
            "https://b.example": {"reliability_score": 100},
        })

        def broken():
            raise RuntimeError("a broke")

        result = guard(
            client, "https://a.example", broken,
            fallbacks=[("https://b.example", lambda: "b-ok")],
        )
        assert result == "b-ok"
