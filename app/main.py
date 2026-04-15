import logging
import mimetypes
import time
from contextlib import asynccontextmanager

mimetypes.add_type("image/webp", ".webp")

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.session import engine
from app.dependencies import Db, RedisClient
from app.site_header import SITE_HEADER_CSS, SITE_HEADER_HTML, SITE_HEADER_JS

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("nemoflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ToolRate API")
    app.state.redis = aioredis.from_url(
        settings.redis_url, decode_responses=True, max_connections=50
    )
    yield
    await app.state.redis.close()
    await engine.dispose()
    logger.info("ToolRate API stopped")


DESCRIPTION = """
**Real advice for every tool your agent considers.**

ToolRate delivers objective, crowdsourced reliability ratings and actionable
intelligence for 600+ external tools and APIs &mdash; based on thousands of real
agent executions across production workloads. Know before you call. Choose
correctly the first time.

## How it works

1. **Assess** before calling a tool — reliability score, failure risk, confidence interval, jurisdiction posture, common pitfalls, and ranked alternatives on every response.
2. **Report** after calling a tool — every success/failure strengthens the data pool for the next agent making the same decision.
3. **Guard** for one-line production use — `guard()` wraps any call, auto-fallback runs on failure, journey data flows back automatically.

## Authentication

All endpoints require an API key passed via the `X-Api-Key` header.

```
X-Api-Key: nf_live_your_key_here
```

## Rate Limits

| Tier | Daily Limit |
|------|------------|
| Free | 100 assessments / day |
| Pay-as-you-go | 100 free / day, then $0.008 per assessment |
| Pro | 10,000 assessments / month ($29/mo flat) |
| Enterprise | Custom |

## SDKs — Python

**Recommended (modern & fastest):**

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add ToolRate to your project
uv add toolrate
```

**Alternative (without uv):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install toolrate
```

> **Note:** If you see a `PEP 668` "externally-managed-environment" error with plain `pip`, that is because of Homebrew Python. Use one of the methods above instead.

## SDKs — TypeScript / Node.js

```bash
npm install toolrate
```

Node 18+ required.
"""

app = FastAPI(
    title="ToolRate",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "ToolRate", "url": "https://toolrate.ai"},
    openapi_tags=[
        {"name": "Auth", "description": "Register for an API key"},
        {"name": "Assessment", "description": "Check tool reliability before calling"},
        {"name": "Reporting", "description": "Report execution results to build the data moat"},
        {"name": "Discovery", "description": "Discover hidden gem tools and fallback chains based on real agent journeys"},
        {"name": "Stats", "description": "Platform and personal usage statistics"},
        {"name": "Webhooks", "description": "Register webhooks for real-time score change alerts"},
        {"name": "Billing", "description": "Upgrade to Pro tier via Stripe"},
    ],
)

# ── Duplicate-content guard ───────────────────────────────────────────────
# Both `toolrate.ai` (marketing + content) and `api.toolrate.ai` (API +
# developer docs) resolve to the same FastAPI app, so every path would be
# reachable under both hostnames and Google + LLM crawlers would see byte-
# for-byte duplicates. The middleware below:
#   1. 301-redirects marketing paths from the api subdomain to apex,
#   2. 301-redirects `api.toolrate.ai/` → `api.toolrate.ai/docs` (developers
#      expect Swagger UI on the API host, not a marketing landing page),
#   3. serves api-only paths on the apex with a noindex header + HTTP
#      `Link: rel="canonical"` pointing at `api.toolrate.ai/<path>` so
#      bookmarks still work but search engines consolidate on the api host,
#   4. normalises `www.toolrate.ai` → `toolrate.ai`.
APEX_HOST = "toolrate.ai"
API_HOST = "api.toolrate.ai"

# Paths that live on the apex only. If requested on the api host, 301 them
# to apex. Root `/` is handled separately (redirects to /docs instead).
_APEX_ONLY_PATHS: frozenset[str] = frozenset({
    "/demo", "/pricing", "/register", "/privacy",
    "/dashboard", "/me", "/upgrade",
    "/llms.txt", "/llms-full.txt",
    "/sitemap.xml", "/robots.txt",
    "/favicon.ico",
    "/toolrate-favicon.png", "/toolrate-logo.webp", "/toolrate-og.jpg",
})
_APEX_ONLY_PREFIXES: tuple[str, ...] = (
    "/billing/",
    "/llms/",
    "/static/",
)

# Paths that are canonically served on `api.toolrate.ai`. On the apex they
# still work (no redirect, so bookmarks don't break), but the response
# carries noindex + a canonical header pointing at the api host.
_API_ONLY_PATHS: frozenset[str] = frozenset({
    "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect",
})
_API_ONLY_PREFIXES: tuple[str, ...] = ("/v1/",)


def _is_apex_only(path: str) -> bool:
    return path in _APEX_ONLY_PATHS or any(path.startswith(p) for p in _APEX_ONLY_PREFIXES)


def _is_api_only(path: str) -> bool:
    return path in _API_ONLY_PATHS or any(path.startswith(p) for p in _API_ONLY_PREFIXES)


def _with_query(url: str, query: str) -> str:
    return f"{url}?{query}" if query else url


@app.middleware("http")
async def host_router(request: Request, call_next):
    host = (request.headers.get("host") or "").lower().split(":", 1)[0]
    path = request.url.path
    query = request.url.query

    # www.toolrate.ai → toolrate.ai (standard apex redirect)
    if host == f"www.{APEX_HOST}":
        return RedirectResponse(
            url=_with_query(f"https://{APEX_HOST}{path}", query),
            status_code=301,
        )

    if host == API_HOST:
        # Developers hitting the API host should land on Swagger, not
        # the marketing homepage.
        if path == "/":
            return RedirectResponse(
                url=f"https://{API_HOST}/docs",
                status_code=301,
            )
        # Marketing / content paths have no business on the API host.
        if _is_apex_only(path):
            return RedirectResponse(
                url=_with_query(f"https://{APEX_HOST}{path}", query),
                status_code=301,
            )
        # Otherwise let the request through (API endpoints, /docs, /redoc,
        # /openapi.json, /health*). The response is canonical for the
        # api host — no extra headers needed.
        return await call_next(request)

    if host == APEX_HOST:
        # API-only paths on the apex: serve them (bookmarks, SDK fallbacks)
        # but tell search engines they are not the canonical.
        if _is_api_only(path):
            response = await call_next(request)
            response.headers["X-Robots-Tag"] = "noindex, follow"
            canonical = f'<https://{API_HOST}{path}>; rel="canonical"'
            existing_link = response.headers.get("Link")
            response.headers["Link"] = (
                f"{existing_link}, {canonical}" if existing_link else canonical
            )
            return response
        # Apex-canonical paths — nothing special to do, handler controls
        # its own canonical (`<link rel="canonical">` in the HTML).
        return await call_next(request)

    # Unknown host (direct IP hit, staging, localhost, etc.) — pass through.
    return await call_next(request)


# CORS — restrict to own domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://toolrate.ai",
        "https://www.toolrate.ai",
        "https://api.toolrate.ai",
        # Legacy origins — kept during domain transition so any cached
        # pages served from the old host still talk to the API.
        "https://nemoflow.ai",
        "https://www.nemoflow.ai",
        "https://api.nemoflow.ai",
    ],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-Api-Key", "Content-Type"],
    max_age=600,
)

# Brand assets — logo and favicon served from the FastAPI app so they
# live at https://toolrate.ai/toolrate-logo.webp (and /toolrate-favicon.png).
# The files live in app/static/ and are deployed with the app image.
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/toolrate-logo.webp", include_in_schema=False)
async def brand_logo():
    return FileResponse("app/static/toolrate-logo.webp", media_type="image/webp")


@app.get("/toolrate-favicon.png", include_in_schema=False)
async def brand_favicon():
    return FileResponse("app/static/toolrate-favicon.png", media_type="image/png")


@app.get("/toolrate-og.jpg", include_in_schema=False)
async def brand_og_image():
    return FileResponse("app/static/toolrate-og.jpg", media_type="image/jpeg")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse("app/static/toolrate-favicon.png", media_type="image/png")


# Security headers + request logging + timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s %s %sms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    # Rate limit headers (set during auth in dependencies.py)
    if hasattr(request.state, "rate_limit"):
        response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_remaining)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=()"
    return response


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


from app.api.v1.router import router as v1_router  # noqa: E402

app.include_router(v1_router)


def _humanize_count(n: int) -> str:
    """Format a large integer for display ('94,747' → '94K', '1,230,000' → '1.2M')."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


async def _get_landing_stats(db, redis) -> tuple[int, int]:
    """Return (tool_count, report_count), cached in Redis for 5 minutes.

    The homepage is rendered with live DB counts so the readout never drifts
    past reality. Without the cache, every home-page hit would cost two
    `SELECT count(*)` queries; with the 5-minute TTL the cost amortises to
    essentially zero even under heavy traffic.
    """
    import json
    from sqlalchemy import select, func
    from app.models.tool import Tool
    from app.models.report import ExecutionReport

    cache_key = "landing:stats:v1"
    raw = await redis.get(cache_key)
    if raw:
        try:
            data = json.loads(raw)
            return int(data["tools"]), int(data["reports"])
        except (ValueError, KeyError, TypeError):
            pass

    tool_count = (await db.execute(select(func.count()).select_from(Tool))).scalar() or 0
    report_count = (await db.execute(select(func.count()).select_from(ExecutionReport))).scalar() or 0
    await redis.set(
        cache_key,
        json.dumps({"tools": int(tool_count), "reports": int(report_count)}),
        ex=300,
    )
    return int(tool_count), int(report_count)


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def root(db: Db, redis: RedisClient):
    from app.landing import LANDING_HTML_TEMPLATE

    try:
        tools, reports = await _get_landing_stats(db, redis)
    except Exception:
        # Never break the homepage because of a DB/cache hiccup — fall back
        # to conservative placeholder numbers so visitors always see a
        # coherent readout.
        logger.exception("Landing stats fetch failed; using static fallback")
        tools, reports = 800, 94000

    html = (
        LANDING_HTML_TEMPLATE
        .replace("__LANDING_TOOLS_COUNT__", f"{tools:,}")
        .replace("__LANDING_REPORTS_COUNT__", _humanize_count(reports))
    )
    return html


@app.get("/demo", include_in_schema=False, response_class=HTMLResponse)
async def demo_page():
    from app.demo_page import DEMO_HTML
    return DEMO_HTML


@app.get("/privacy", include_in_schema=False, response_class=HTMLResponse)
async def privacy_page():
    from app.privacy_page import PRIVACY_HTML
    return PRIVACY_HTML


@app.get("/register", include_in_schema=False, response_class=HTMLResponse)
async def register_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ToolRate — Get Your API Key</title>
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--brand:#0a95fd;--brand-dim:rgba(10,149,253,0.08);--border:#1c1f2e;--border-strong:#282c40;--surface:#0f1118;--text-bright:#f0f2f8}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Poppins','Segoe UI',Arial,sans-serif;background:#0a0b10;color:#d4d8e8;min-height:100vh;display:flex;flex-direction:column}
.register-wrap{flex:1;display:flex;justify-content:center;align-items:center;padding:2rem 0}
.card{max-width:440px;width:100%;margin:0 2rem;padding:2.5rem;background:#0f1118;border:1px solid #1c1f2e;border-radius:16px}
h1{font-size:1.5rem;font-weight:700;color:#f0f2f8;margin-bottom:0.4rem}
.sub{font-size:0.85rem;color:#9299b0;margin-bottom:2rem;line-height:1.5}
label{display:block;font-size:0.78rem;font-weight:500;color:#9299b0;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.05em}
input{width:100%;padding:0.75rem 1rem;background:#141620;border:1px solid #282c40;border-radius:8px;color:#f0f2f8;font-family:inherit;font-size:0.9rem;outline:none;transition:border-color 0.2s}
input:focus{border-color:#0a95fd}
input::placeholder{color:#5a5f75}
.btn{width:100%;padding:0.8rem;margin-top:1.25rem;background:#0a95fd;color:#fff;border:none;border-radius:8px;font-family:inherit;font-size:0.9rem;font-weight:700;cursor:pointer;transition:all 0.2s}
.btn:hover{background:#0784e6;box-shadow:0 0 30px rgba(10,149,253,0.2)}
.btn:disabled{opacity:0.5;cursor:not-allowed}
.result{display:none;margin-top:1.5rem;padding:1.25rem;background:#141620;border:1px solid #282c40;border-radius:10px}
.result h3{font-size:0.85rem;font-weight:600;color:#0a95fd;margin-bottom:0.5rem}
.key-box{font-family:'Fira Code',monospace;font-size:0.82rem;color:#f0f2f8;background:#0a0b10;padding:0.75rem 1rem;border-radius:6px;border:1px solid #282c40;word-break:break-all;margin-bottom:0.75rem;position:relative;cursor:pointer;transition:border-color 0.2s}
.key-box:hover{border-color:#0a95fd}
.key-box .copy-hint{position:absolute;right:0.75rem;top:50%;transform:translateY(-50%);font-size:0.65rem;color:#9299b0;font-family:'Poppins',sans-serif}
.warning{font-size:0.75rem;color:#f0c53b;line-height:1.5}
.error{display:none;margin-top:1rem;padding:0.75rem 1rem;background:rgba(240,90,90,0.08);border:1px solid rgba(240,90,90,0.2);border-radius:8px;font-size:0.82rem;color:#f05a5a}
.privacy{font-size:0.7rem;color:#6a6f85;margin-top:1rem;line-height:1.5;text-align:center}
.back{display:block;text-align:center;margin-top:1.5rem;font-size:0.8rem;color:#9299b0;text-decoration:none}
.back:hover{color:#0a95fd}
""" + SITE_HEADER_CSS + """
</style>
</head>
<body>
""" + SITE_HEADER_HTML + """
<div class="register-wrap">
<div class="card">
  <h1>Get your API key</h1>
  <p class="sub">Free tier — 100 calls/day. No credit card required.</p>

  <form id="regForm" onsubmit="return handleRegister(event)">
    <label for="email">Email address</label>
    <input type="email" id="email" name="email" placeholder="you@example.com" required>
    <button type="submit" class="btn" id="submitBtn">Generate API Key</button>
  </form>

  <div class="error" id="error"></div>

  <div class="result" id="result">
    <h3>Your API Key</h3>
    <div class="key-box" id="keyBox" onclick="copyKey()">
      <span id="keyText"></span>
      <span class="copy-hint">click to copy</span>
    </div>
    <p class="warning">Save this key now — it cannot be retrieved later. A copy has been sent to your email.</p>
    <div style="margin-top:1.25rem;padding-top:1.25rem;border-top:1px solid #282c40">
      <p style="font-size:0.82rem;color:#d4d8e8;margin-bottom:0.75rem;font-weight:600">Next: install the SDK</p>

      <p style="font-size:0.7rem;color:#0a95fd;margin:0 0 0.3rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Recommended — modern &amp; fastest</p>
      <pre style="background:#0a0b10;border:1px solid #282c40;border-radius:6px;padding:0.7rem 0.85rem;font-family:'Fira Code',monospace;font-size:0.72rem;color:#d4d8e8;overflow-x:auto;margin:0 0 0.75rem;line-height:1.55"><span style="color:#6a6f85"># Install uv (one-time)</span>
curl -LsSf https://astral.sh/uv/install.sh | sh

<span style="color:#6a6f85"># Add ToolRate to your project</span>
uv add toolrate</pre>

      <p style="font-size:0.7rem;color:#0a95fd;margin:0 0 0.3rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Alternative — without uv</p>
      <pre style="background:#0a0b10;border:1px solid #282c40;border-radius:6px;padding:0.7rem 0.85rem;font-family:'Fira Code',monospace;font-size:0.72rem;color:#d4d8e8;overflow-x:auto;margin:0 0 0.5rem;line-height:1.55">python3 -m venv .venv
source .venv/bin/activate
pip install toolrate</pre>

      <p style="font-size:0.7rem;color:#f0c53b;line-height:1.55;margin:0.5rem 0 0.75rem;padding:0.55rem 0.7rem;background:rgba(240,197,59,0.05);border-left:2px solid rgba(240,197,59,0.55);border-radius:3px"><strong>Note:</strong> If you see a <code style="font-family:'Fira Code',monospace">PEP 668</code> &ldquo;externally-managed-environment&rdquo; error with plain <code style="font-family:'Fira Code',monospace">pip</code>, that&rsquo;s because of Homebrew Python. Use one of the methods above instead.</p>

      <p style="font-size:0.7rem;color:#6a6f85;margin:0">TypeScript: <code style="color:#d4d8e8;font-family:'Fira Code',monospace">npm install toolrate</code> (Node 18+) &middot; <a href="/docs" style="color:#0a95fd;text-decoration:none">API docs</a></p>
    </div>
    <div style="margin-top:1.25rem;padding-top:1.25rem;border-top:1px solid #282c40">
      <p style="font-size:0.82rem;color:#d4d8e8;margin-bottom:0.75rem">Need more than 100 calls/day?</p>
      <a href="/pricing" class="btn" style="display:block;text-align:center;text-decoration:none;margin-top:0">See pricing — PAYG $0.008/call or Pro $29/mo</a>
    </div>
  </div>

  <p class="privacy">Your email is hashed for deduplication only — we never store it in plain text.</p>
  <a href="/" class="back">&larr; Back to ToolRate</a>
</div>
</div>

<script>
async function handleRegister(e) {
  e.preventDefault();
  var btn = document.getElementById('submitBtn');
  var err = document.getElementById('error');
  var res = document.getElementById('result');
  err.style.display = 'none';
  res.style.display = 'none';
  btn.disabled = true;
  btn.textContent = 'Generating...';

  try {
    var resp = await fetch('/v1/auth/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({email: document.getElementById('email').value})
    });
    var data = await resp.json();

    if (!resp.ok) {
      err.textContent = data.detail || 'Something went wrong. Try again.';
      err.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Generate API Key';
      return;
    }

    document.getElementById('keyText').textContent = data.api_key;
    res.style.display = 'block';
    document.getElementById('regForm').style.display = 'none';
  } catch(e) {
    err.textContent = 'Network error. Please try again.';
    err.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Generate API Key';
  }
}

function copyKey() {
  var key = document.getElementById('keyText').textContent;
  navigator.clipboard.writeText(key).then(function() {
    var hint = document.querySelector('.copy-hint');
    hint.textContent = 'copied!';
    hint.style.color = '#0a95fd';
    setTimeout(function() { hint.textContent = 'click to copy'; hint.style.color = '#9299b0'; }, 2000);
  });
}
</script>
""" + SITE_HEADER_JS + """
</body>
</html>"""


@app.get("/pricing", include_in_schema=False, response_class=HTMLResponse)
async def pricing_page():
    from app.pricing_page import PRICING_HTML
    return PRICING_HTML


@app.get("/dashboard", include_in_schema=False, response_class=HTMLResponse)
async def dashboard_page():
    from app.dashboard_page import DASHBOARD_HTML
    return DASHBOARD_HTML


@app.get("/me", include_in_schema=False, response_class=HTMLResponse)
async def me_page():
    from app.me_page import ME_PAGE_HTML
    return ME_PAGE_HTML


@app.get("/upgrade", include_in_schema=False, response_class=HTMLResponse)
async def upgrade_page(plan: str = "payg"):
    if plan not in ("payg", "pro"):
        plan = "payg"

    if plan == "payg":
        title = "Start Pay-as-you-go"
        sub = "100 free assessments every day, then $0.008 each. No monthly commitment."
        badge = "PAYG"
        price_html = '$0.008 <span>/ assessment</span>'
        features = [
            "First 100 assessments / day free",
            "$0.008 per assessment after that",
            "Webhook alerts included",
            "Higher rate limits",
            "Pay only for what you use",
        ]
    else:
        title = "Upgrade to Pro"
        sub = "10,000 assessments per month at a flat $29/month."
        badge = "PRO"
        price_html = '$29 <span>/ month</span>'
        features = [
            "10,000 assessments / month",
            "Priority email support",
            "Webhook score alerts",
            "Higher rate limits",
            "Cancel anytime",
        ]

    features_html = "".join(f"<li>{f}</li>" for f in features)

    # Doubled braces in the CSS/JS below are deliberate — this is an f-string,
    # so single `{` / `}` are f-string interpolation. The shared site header
    # is pre-formatted (not an f-string) so we pre-escape its braces before
    # embedding it below.
    header_css_fstring = SITE_HEADER_CSS.replace("{", "{{").replace("}", "}}")
    header_html_fstring = SITE_HEADER_HTML.replace("{", "{{").replace("}", "}}")
    header_js_fstring = SITE_HEADER_JS.replace("{", "{{").replace("}", "}}")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ToolRate — {title}</title>
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--brand:#0a95fd;--brand-dim:rgba(10,149,253,0.08);--border:#1c1f2e;--border-strong:#282c40;--surface:#0f1118;--text-bright:#f0f2f8}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Poppins','Segoe UI',Arial,sans-serif;background:#0a0b10;color:#d4d8e8;min-height:100vh;display:flex;flex-direction:column}}
.upgrade-wrap{{flex:1;display:flex;justify-content:center;align-items:center;padding:2rem 0}}
.card{{max-width:480px;width:100%;margin:0 2rem;padding:2.5rem;background:#0f1118;border:1px solid #1c1f2e;border-radius:16px}}
h1{{font-size:1.5rem;font-weight:700;color:#f0f2f8;margin-bottom:0.4rem}}
.sub{{font-size:0.85rem;color:#9299b0;margin-bottom:2rem;line-height:1.5}}
.plan{{background:#141620;border:1px solid #0a95fd;border-radius:12px;padding:1.5rem;margin-bottom:2rem;position:relative}}
.plan::before{{content:'{badge}';position:absolute;top:-0.5rem;left:1.25rem;font-size:0.6rem;font-weight:700;letter-spacing:0.08em;color:#fff;background:#0a95fd;padding:0.15rem 0.5rem;border-radius:4px}}
.plan-price{{font-size:2rem;font-weight:700;color:#f0f2f8;margin-bottom:0.25rem}}
.plan-price span{{font-size:0.85rem;font-weight:300;color:#9299b0}}
.plan-features{{list-style:none;margin-top:1rem}}
.plan-features li{{font-size:0.82rem;color:#d4d8e8;padding:0.35rem 0;display:flex;align-items:center;gap:0.5rem}}
.plan-features li::before{{content:'+';color:#0a95fd;font-weight:700}}
label{{display:block;font-size:0.78rem;font-weight:500;color:#9299b0;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.05em}}
input{{width:100%;padding:0.75rem 1rem;background:#141620;border:1px solid #282c40;border-radius:8px;color:#f0f2f8;font-family:'Fira Code',monospace;font-size:0.82rem;outline:none;transition:border-color 0.2s}}
input:focus{{border-color:#0a95fd}}
input::placeholder{{color:#5a5f75}}
.btn{{width:100%;padding:0.8rem;margin-top:1.25rem;background:#0a95fd;color:#fff;border:none;border-radius:8px;font-family:inherit;font-size:0.9rem;font-weight:700;cursor:pointer;transition:all 0.2s}}
.btn:hover{{background:#0784e6;box-shadow:0 0 30px rgba(10,149,253,0.2)}}
.btn:disabled{{opacity:0.5;cursor:not-allowed}}
.error{{display:none;margin-top:1rem;padding:0.75rem 1rem;background:rgba(240,90,90,0.08);border:1px solid rgba(240,90,90,0.2);border-radius:8px;font-size:0.82rem;color:#f05a5a}}
.links{{display:flex;justify-content:space-between;margin-top:1.5rem;flex-wrap:wrap;gap:0.5rem}}
.links a{{font-size:0.78rem;color:#9299b0;text-decoration:none}}
.links a:hover{{color:#0a95fd}}
.switch{{text-align:center;font-size:0.78rem;color:#9299b0;margin-top:0.75rem}}
.switch a{{color:#0a95fd;text-decoration:none;font-weight:500}}
{header_css_fstring}
</style>
</head>
<body>
{header_html_fstring}
<div class="upgrade-wrap">
<div class="card">
  <h1>{title}</h1>
  <p class="sub">{sub}</p>

  <div class="plan">
    <div class="plan-price">{price_html}</div>
    <ul class="plan-features">
      {features_html}
    </ul>
  </div>

  <form id="upgradeForm" onsubmit="return handleUpgrade(event)">
    <label for="apiKey">Your API Key</label>
    <input type="text" id="apiKey" name="apiKey" placeholder="nf_live_..." required>
    <button type="submit" class="btn" id="submitBtn">Continue to Payment</button>
  </form>

  <div class="error" id="error"></div>

  <p class="switch">
    { 'Prefer the flat $29/month Pro plan? <a href="/upgrade?plan=pro">Switch</a>' if plan == 'payg' else 'Prefer pay-as-you-go? <a href="/upgrade?plan=payg">Switch</a>' }
  </p>

  <div class="links">
    <a href="/pricing">&larr; Back to Pricing</a>
    <a href="/register">Need an API key first?</a>
  </div>
</div>
</div>

<script>
async function handleUpgrade(e) {{
  e.preventDefault();
  var btn = document.getElementById('submitBtn');
  var err = document.getElementById('error');
  err.style.display = 'none';
  btn.disabled = true;
  btn.textContent = 'Redirecting to Stripe...';

  try {{
    var resp = await fetch('/v1/billing/checkout?plan={plan}', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'X-Api-Key': document.getElementById('apiKey').value.trim()
      }}
    }});
    var data = await resp.json();

    if (!resp.ok) {{
      err.textContent = data.detail || 'Invalid API key or billing not available.';
      err.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Continue to Payment';
      return;
    }}

    window.location.href = data.checkout_url;
  }} catch(e) {{
    err.textContent = 'Network error. Please try again.';
    err.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Continue to Payment';
  }}
}}
</script>
{header_js_fstring}
</body>
</html>"""


@app.get("/billing/success", include_in_schema=False, response_class=HTMLResponse)
async def billing_success(plan: str = "pro"):
    if plan == "payg":
        heading = "You're on Pay-as-you-go"
        body_html = (
            '<p>Your API key is now on the Pay-as-you-go plan. The first '
            '<strong style="color:#f0f2f8">100 assessments every day</strong> '
            'are free, and any further calls are billed at '
            '<strong style="color:#f0f2f8">$0.008 each</strong>. Usage resets at midnight UTC.</p>'
        )
    else:
        heading = "Welcome to Pro"
        body_html = (
            '<p>Your API key has been upgraded to '
            '<strong style="color:#f0f2f8">10,000 assessments per month</strong>. '
            'The change is effective immediately.</p>'
        )
    header_css_fstring = SITE_HEADER_CSS.replace("{", "{{").replace("}", "}}")
    header_html_fstring = SITE_HEADER_HTML.replace("{", "{{").replace("}", "}}")
    header_js_fstring = SITE_HEADER_JS.replace("{", "{{").replace("}", "}}")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>ToolRate — {heading}</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<style>
:root{{--brand:#0a95fd;--brand-dim:rgba(10,149,253,0.08);--border:#1c1f2e;--border-strong:#282c40;--surface:#0f1118;--text-bright:#f0f2f8}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Poppins',sans-serif;background:#0a0b10;color:#d4d8e8;min-height:100vh;display:flex;flex-direction:column}}
.billing-wrap{{flex:1;display:flex;justify-content:center;align-items:center;padding:2rem 0}}
.card{{text-align:center;max-width:480px;padding:3rem;margin:0 2rem;background:#0f1118;border:1px solid #1c1f2e;border-radius:16px}}
h1{{font-size:1.5rem;color:#0a95fd;margin-bottom:1rem}}p{{color:#9299b0;line-height:1.6;font-size:0.9rem}}
a{{color:#0a95fd;text-decoration:none;font-weight:600}}a:hover{{text-decoration:underline}}
{header_css_fstring}
</style></head>
<body>
{header_html_fstring}
<div class="billing-wrap"><div class="card"><h1>{heading}</h1>
{body_html}
<p style="margin-top:1.5rem"><a href="/docs">Go to API Docs &rarr;</a></p></div></div>
{header_js_fstring}
</body></html>"""


@app.get("/billing/cancel", include_in_schema=False, response_class=HTMLResponse)
async def billing_cancel():
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><title>ToolRate — Checkout Cancelled</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<style>
:root{--brand:#0a95fd;--brand-dim:rgba(10,149,253,0.08);--border:#1c1f2e;--border-strong:#282c40;--surface:#0f1118;--text-bright:#f0f2f8}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Poppins',sans-serif;background:#0a0b10;color:#d4d8e8;min-height:100vh;display:flex;flex-direction:column}
.billing-wrap{flex:1;display:flex;justify-content:center;align-items:center;padding:2rem 0}
.card{text-align:center;max-width:480px;padding:3rem;margin:0 2rem;background:#0f1118;border:1px solid #1c1f2e;border-radius:16px}
h1{font-size:1.5rem;color:#9299b0;margin-bottom:1rem}p{color:#9299b0;line-height:1.6;font-size:0.9rem}
a{color:#0a95fd;text-decoration:none;font-weight:600}a:hover{text-decoration:underline}
""" + SITE_HEADER_CSS + """
</style></head>
<body>
""" + SITE_HEADER_HTML + """
<div class="billing-wrap"><div class="card"><h1>Checkout Cancelled</h1>
<p>No charges were made. You can upgrade anytime.</p>
<p style="margin-top:1.5rem"><a href="/upgrade">&larr; Try again</a> &nbsp;&middot;&nbsp; <a href="/">Back to ToolRate</a></p></div></div>
""" + SITE_HEADER_JS + """
</body></html>"""


async def _render_llms_doc(template: str, db: Db, redis: RedisClient) -> str:
    """Fill the __LANDING_*__ placeholders in llms.txt / llms-full.txt.

    Reuses the same 5-minute stats cache as the homepage so every
    crawler-facing doc surfaces the same live numbers.
    """
    try:
        tools, reports = await _get_landing_stats(db, redis)
    except Exception:
        logger.exception("llms.txt stats fetch failed; using static fallback")
        tools, reports = 800, 94000
    return (
        template
        .replace("__LANDING_TOOLS_COUNT__", f"{tools:,}")
        .replace("__LANDING_REPORTS_COUNT__", f"{reports:,}")
    )


@app.api_route("/llms.txt", methods=["GET", "HEAD"], include_in_schema=False, response_class=PlainTextResponse)
async def llms_txt(db: Db, redis: RedisClient):
    from app.llms import LLMS_TXT
    return await _render_llms_doc(LLMS_TXT, db, redis)


@app.api_route("/llms-full.txt", methods=["GET", "HEAD"], include_in_schema=False, response_class=PlainTextResponse)
async def llms_full_txt(db: Db, redis: RedisClient):
    from app.llms import LLMS_FULL_TXT
    return await _render_llms_doc(LLMS_FULL_TXT, db, redis)


@app.api_route(
    "/llms/toolrate-{lang}.md",
    methods=["GET", "HEAD"],
    include_in_schema=False,
)
async def llms_translation(lang: str):
    """Serve a single-language ToolRate overview (llmstxt.org multilingual).

    Sets `Content-Language` to the correct BCP 47 tag, emits HTTP `Link`
    headers with `rel=alternate; hreflang=<code>` for every sibling
    translation plus `rel=canonical` pointing at the top-level `/llms.txt`.
    The `lang` parameter is validated against the `TRANSLATIONS` whitelist,
    so the path cannot be used for directory traversal.
    """
    from app.llms import TRANSLATIONS, load_translation

    content = load_translation(lang)
    if content is None:
        raise HTTPException(status_code=404, detail="Translation not found")

    alternates = [
        f'<https://toolrate.ai/llms/toolrate-{code}.md>; rel="alternate"; hreflang="{code}"'
        for code in TRANSLATIONS
    ]
    alternates.append('<https://toolrate.ai/llms.txt>; rel="alternate"; hreflang="x-default"')
    alternates.append('<https://toolrate.ai/llms.txt>; rel="canonical"')

    headers = {
        "Content-Language": lang,
        "Link": ", ".join(alternates),
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
        "X-Robots-Tag": "index, follow",
    }
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )


@app.api_route("/robots.txt", methods=["GET", "HEAD"], include_in_schema=False, response_class=PlainTextResponse)
async def robots_txt(request: Request):
    """Host-aware robots.txt.

    `toolrate.ai` (apex) lists the full site, points at the sitemap, and
    only disallows the JSON API endpoints. `api.toolrate.ai` only exposes
    the developer-facing doc surfaces (`/docs`, `/redoc`, `/openapi.json`),
    disallows everything else, and intentionally omits a `Sitemap:` line
    so crawlers pick up the single canonical sitemap from the apex.
    """
    from app.llms import ROBOTS_TXT_APEX, ROBOTS_TXT_API

    host = (request.headers.get("host") or "").lower().split(":", 1)[0]
    return ROBOTS_TXT_API if host == API_HOST else ROBOTS_TXT_APEX


@app.api_route("/sitemap.xml", methods=["GET", "HEAD"], include_in_schema=False)
async def sitemap_xml():
    # Google/Bing require application/xml on sitemaps — they treat
    # text/plain as "probably not a sitemap" and skip it. PlainTextResponse
    # was silently breaking discoverability of every page listed here.
    from datetime import datetime, timezone

    from app.llms import TRANSLATIONS

    lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build hreflang alternates block — reused for every translation entry
    # so that search engines and LLM crawlers understand the cross-language
    # relationships (reciprocal hreflang is a Google hard requirement).
    alt_lines = "".join(
        f'\n    <xhtml:link rel="alternate" hreflang="{code}" '
        f'href="https://toolrate.ai/llms/toolrate-{code}.md"/>'
        for code in TRANSLATIONS
    )
    alt_lines += (
        '\n    <xhtml:link rel="alternate" hreflang="x-default" '
        'href="https://toolrate.ai/llms.txt"/>'
    )

    translation_entries = "\n".join(
        f"""  <url>
    <loc>https://toolrate.ai/llms/toolrate-{code}.md</loc>
    <lastmod>{lastmod}</lastmod>
    <priority>0.6</priority>{alt_lines}
  </url>"""
        for code in TRANSLATIONS
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url><loc>https://toolrate.ai/</loc><lastmod>{lastmod}</lastmod><priority>1.0</priority></url>
  <url><loc>https://toolrate.ai/demo</loc><lastmod>{lastmod}</lastmod><priority>0.95</priority></url>
  <url><loc>https://toolrate.ai/pricing</loc><lastmod>{lastmod}</lastmod><priority>0.9</priority></url>
  <url><loc>https://toolrate.ai/register</loc><lastmod>{lastmod}</lastmod><priority>0.8</priority></url>
  <url><loc>https://toolrate.ai/privacy</loc><lastmod>{lastmod}</lastmod><priority>0.4</priority></url>
  <url><loc>https://toolrate.ai/llms.txt</loc><lastmod>{lastmod}</lastmod><priority>0.7</priority></url>
  <url><loc>https://toolrate.ai/llms-full.txt</loc><lastmod>{lastmod}</lastmod><priority>0.7</priority></url>
  <url><loc>https://api.toolrate.ai/docs</loc><lastmod>{lastmod}</lastmod><priority>0.9</priority></url>
  <url><loc>https://api.toolrate.ai/redoc</loc><lastmod>{lastmod}</lastmod><priority>0.9</priority></url>
{translation_entries}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@app.get("/health")
async def health(request: Request):
    """Liveness check — always 200 so the restart cron doesn't thrash on DB hiccups.
    Use /health/ready for readiness (503 if a dependency is down)."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(request: Request):
    checks: dict[str, str] = {}
    ok = True

    try:
        from sqlalchemy import text
        from app.db.session import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("Readiness DB failure: %s", exc)
        checks["database"] = "error"
        ok = False

    try:
        pong = await request.app.state.redis.ping()
        checks["redis"] = "ok" if pong else "error"
        if not pong:
            ok = False
    except Exception as exc:
        logger.warning("Readiness Redis failure: %s", exc)
        checks["redis"] = "error"
        ok = False

    return JSONResponse(
        status_code=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )
