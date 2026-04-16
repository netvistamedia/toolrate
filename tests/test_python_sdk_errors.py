"""Python SDK robustness against malformed server responses.

The SDK used to do ``resp.raise_for_status(); return resp.json()`` in every
method. When an upstream proxy returned a 200 with empty / non-JSON body,
``resp.json()`` raised a bare ``json.JSONDecodeError`` that caller code had
no way to catch by type. The TS SDK was fixed in commit f4f9b41; this test
file covers the parallel Python fix introduced in 0.5.0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

# SDK lives outside the installed packages — make it importable.
_SDK_PATH = str(Path(__file__).resolve().parent.parent / "sdks" / "python")
if _SDK_PATH not in sys.path:
    sys.path.insert(0, _SDK_PATH)

from toolrate import ToolRate, ToolRateError  # noqa: E402
from toolrate.client import _parse_json_or_raise  # noqa: E402


def _mock_response(*, status: int = 200, body: str | None = None, json_obj=None) -> MagicMock:
    """Build a fake httpx.Response just rich enough for _parse_json_or_raise.

    Tests that need ``resp.json()`` to raise pass body=non-JSON; tests that
    need a clean dict pass json_obj.
    """
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.reason_phrase = httpx.codes.get_reason_phrase(status)
    resp.text = body if body is not None else (json.dumps(json_obj) if json_obj is not None else "")

    if status >= 400:
        def _raise():
            req = httpx.Request("POST", "https://api.toolrate.ai/test")
            raise httpx.HTTPStatusError(
                f"{status}", request=req, response=resp,
            )
        resp.raise_for_status.side_effect = _raise
    else:
        resp.raise_for_status.return_value = None

    if json_obj is not None:
        resp.json.return_value = json_obj
    elif body is None or body == "":
        resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    else:
        try:
            parsed = json.loads(body)
            resp.json.return_value = parsed
        except json.JSONDecodeError as e:
            resp.json.side_effect = e

    return resp


class TestParseJsonOrRaise:
    def test_returns_parsed_dict_on_2xx(self):
        resp = _mock_response(status=200, json_obj={"ok": True})
        assert _parse_json_or_raise(resp) == {"ok": True}

    def test_empty_body_on_2xx_raises_toolrate_error(self):
        """The exact scenario the bug describes: 200 with no body would
        previously crash the caller with JSONDecodeError. Must be a
        ``ToolRateError`` so callers can ``except ToolRateError`` once
        and cover all server-side failure modes."""
        resp = _mock_response(status=200, body="")
        with pytest.raises(ToolRateError) as exc_info:
            _parse_json_or_raise(resp)
        assert exc_info.value.status == 200
        assert "unparseable" in str(exc_info.value).lower()

    def test_html_body_on_2xx_raises_toolrate_error(self):
        """An upstream proxy serving an HTML maintenance page with HTTP 200
        is the most common shape of this bug in production."""
        resp = _mock_response(status=200, body="<html><body>maintenance</body></html>")
        with pytest.raises(ToolRateError) as exc_info:
            _parse_json_or_raise(resp)
        assert exc_info.value.status == 200

    def test_json_null_on_2xx_raises_toolrate_error(self):
        """A literal ``null`` parses fine but means there's no payload — must
        not be returned as ``None`` to the caller (their downstream code
        will dereference it)."""
        resp = _mock_response(status=200, json_obj=None)
        # JSON 'null' parses to None, then our helper rejects it
        resp.json.side_effect = None
        resp.json.return_value = None
        resp.text = "null"
        with pytest.raises(ToolRateError) as exc_info:
            _parse_json_or_raise(resp)
        assert exc_info.value.status == 200

    def test_4xx_with_json_error_body_carries_through(self):
        """Structured 422 error body should be available on ``err.body`` so
        callers can branch on the validation message."""
        resp = _mock_response(status=422, json_obj={"detail": "missing field"})
        with pytest.raises(ToolRateError) as exc_info:
            _parse_json_or_raise(resp)
        assert exc_info.value.status == 422
        assert exc_info.value.body == {"detail": "missing field"}

    def test_5xx_with_html_body_does_not_crash(self):
        """A 502 from an upstream proxy with an HTML body must surface as
        ``ToolRateError(status=502)`` with the truncated text on body."""
        resp = _mock_response(status=502, body="<html>bad gateway</html>")
        with pytest.raises(ToolRateError) as exc_info:
            _parse_json_or_raise(resp)
        assert exc_info.value.status == 502
        assert "bad gateway" in (exc_info.value.body or "")


class TestEndToEndMalformedAssess:
    """Full SDK call path: assess() against a transport returning malformed body."""

    def test_assess_raises_toolrate_error_on_malformed_body(self, monkeypatch):
        client = ToolRate("nf_test_fake")

        def mock_post(self, *args, **kwargs):
            return _mock_response(status=200, body="not-json-at-all")

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        with pytest.raises(ToolRateError) as exc_info:
            client.assess("https://api.example.com")
        assert exc_info.value.status == 200
        client.close()

    def test_assess_raises_toolrate_error_on_500_html(self, monkeypatch):
        client = ToolRate("nf_test_fake")

        def mock_post(self, *args, **kwargs):
            return _mock_response(status=500, body="<html>internal error</html>")

        monkeypatch.setattr(httpx.Client, "post", mock_post)

        with pytest.raises(ToolRateError) as exc_info:
            client.assess("https://api.example.com")
        assert exc_info.value.status == 500
        client.close()
