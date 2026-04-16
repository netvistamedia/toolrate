"""Tool identifier normalization.

Without normalization, ``https://API.Stripe.com/v1/charges/`` and
``https://api.stripe.com/v1/charges`` would land as two rows in the
``tools`` table — twice the storage, half the report density on each
score. This module is the single source of truth for the canonical
form. Apply at every write site (report ingest, assess upsert, seed)
and at every read site (assess lookup) so the two converge.

Rules:

* URLs (``http://`` / ``https://`` prefix): lowercase scheme + host,
  strip default port (80/443), strip trailing slash from path, drop
  fragment but keep query string (it can be semantically meaningful for
  REST endpoints like ``?action=create``).
* Non-URL identifiers (bare names, package handles): lowercase + trim.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}


def normalize_identifier(raw: str | None) -> str:
    """Return the canonical form of a tool identifier.

    Idempotent — running the result through ``normalize_identifier`` again
    returns the same value. ``None`` and empty input pass through to ``""``
    so callers can safely chain without a None check.
    """
    if not raw:
        return ""

    s = raw.strip()
    if not s:
        return ""

    lower = s.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        # Bare identifier (e.g. "stripe", "openai/api"). Just normalize case
        # and whitespace.
        return lower

    parts = urlsplit(s)
    scheme = parts.scheme.lower()
    host = parts.hostname.lower() if parts.hostname else ""

    netloc = host
    if parts.port is not None and _DEFAULT_PORTS.get(scheme) != parts.port:
        netloc = f"{host}:{parts.port}"

    path = parts.path or ""
    # Strip trailing slash, but keep "/" → "" so root URLs land at
    # https://example.com (not https://example.com/) for stable comparison.
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")
    elif path == "/":
        path = ""

    # Drop fragment (never semantically meaningful for an API tool); preserve
    # the query string verbatim — REST endpoints sometimes carry meaningful
    # query params (?action=create, ?type=foo) that distinguish endpoints.
    return urlunsplit((scheme, netloc, path, parts.query, ""))
