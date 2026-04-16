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


class TestIdnaNormalization:
    """IDNA encoding folds visually-identical hostnames onto stable canonicals
    so a Cyrillic 'ѕtripe.com' lookalike can't pretend to be 'stripe.com' in
    discovery / fallback-chain queries."""

    def test_pure_ascii_unchanged(self):
        """ASCII hostnames stay byte-identical (no surprise punycode)."""
        assert (
            normalize_identifier("https://api.stripe.com/v1/charges")
            == "https://api.stripe.com/v1/charges"
        )

    def test_cyrillic_lookalike_punycode(self):
        """Cyrillic 'ѕ' (U+0455) host is encoded to its punycode form so the
        canonical ID is unambiguous and visibly distinguishable from the
        Latin spelling — different domain, different row, no silent merge."""
        # 'ѕtripe.com' starts with U+0455 CYRILLIC SMALL LETTER DZE
        result = normalize_identifier("https://\u0455tripe.com/v1/charges")
        assert result.startswith("https://xn--")
        assert "stripe" not in result.split("/")[2]  # host segment

    def test_idna_idempotent(self):
        """Re-normalizing the IDNA result returns the same string."""
        once = normalize_identifier("https://\u0455tripe.com/v1/charges")
        twice = normalize_identifier(once)
        assert once == twice

    def test_invalid_idna_falls_back_to_lowercased_original(self):
        """Hosts that fail IDNA validation (e.g. underscore in label) still
        normalize to a lowercased form rather than 500-ing the request."""
        # Underscore is not legal in IDNA labels — fallback should handle it.
        result = normalize_identifier("https://my_service.example.com/v1")
        assert result == "https://my_service.example.com/v1"
