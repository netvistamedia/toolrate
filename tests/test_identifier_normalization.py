"""Tool-identifier normalization — single source of truth for canonical form.

Without this, ``https://API.Stripe.com/v1/charges/`` and
``https://api.stripe.com/v1/charges`` were two distinct rows in ``tools``,
fragmenting reports + scores across what should be one endpoint.
"""

import pytest

from app.core.identifiers import normalize_identifier


class TestNormalizeIdentifier:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            # Lowercase host
            ("https://API.Stripe.com/v1/charges", "https://api.stripe.com/v1/charges"),
            # Strip trailing slash
            ("https://api.stripe.com/v1/charges/", "https://api.stripe.com/v1/charges"),
            # Both at once — the shape that motivated the bug
            ("https://API.Stripe.com/v1/charges/", "https://api.stripe.com/v1/charges"),
            # Lowercase scheme
            ("HTTPS://api.stripe.com/v1/charges", "https://api.stripe.com/v1/charges"),
            # Default port stripped
            ("https://api.stripe.com:443/v1/charges", "https://api.stripe.com/v1/charges"),
            ("http://api.example.com:80/v1", "http://api.example.com/v1"),
            # Non-default port preserved
            ("http://api.example.com:8080/v1", "http://api.example.com:8080/v1"),
            # Drop fragment
            ("https://api.example.com/v1#section", "https://api.example.com/v1"),
            # Preserve query string (semantically meaningful)
            ("https://api.example.com/?action=create", "https://api.example.com?action=create"),
            # Whitespace
            ("  https://api.stripe.com/v1/charges  ", "https://api.stripe.com/v1/charges"),
            # Bare-name identifier (lowercase + trim)
            ("Stripe", "stripe"),
            ("  OpenAI/api  ", "openai/api"),
            # None / empty pass through
            (None, ""),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_normalization_cases(self, raw, expected):
        assert normalize_identifier(raw) == expected

    def test_idempotent(self):
        """Running the result through normalize_identifier again is a no-op."""
        once = normalize_identifier("https://API.Stripe.com/v1/charges/")
        twice = normalize_identifier(once)
        assert once == twice

    def test_root_url_collapses_trailing_slash(self):
        """https://example.com/ → https://example.com so the trailing slash
        doesn't fragment a domain-level identifier."""
        assert normalize_identifier("https://example.com/") == "https://example.com"
        assert normalize_identifier("https://example.com") == "https://example.com"
