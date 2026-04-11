import logging
import time
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import settings
from app.db.session import engine

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("nemoflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NemoFlow API")
    app.state.redis = aioredis.from_url(
        settings.redis_url, decode_responses=True, max_connections=50
    )
    yield
    await app.state.redis.close()
    await engine.dispose()
    logger.info("NemoFlow API stopped")


DESCRIPTION = """
**The reliability oracle for AI agents.**

NemoFlow provides real-time reliability scores for external tools and APIs,
based on the collective experience of thousands of AI agents.

## How it works

1. **Assess** before calling a tool — get a reliability score, failure risk, common pitfalls, and alternatives
2. **Report** after calling a tool — contribute success/failure data back to the community
3. The data moat grows with every report, making scores more accurate for everyone

## Authentication

All endpoints require an API key passed via the `X-Api-Key` header.

```
X-Api-Key: nf_live_your_key_here
```

## Rate Limits

| Tier | Daily Limit |
|------|------------|
| Free | 100 calls |
| Pro | 10,000 calls |
| Enterprise | Custom |

## SDKs

- **Python**: `pip install nemoflow`
- **TypeScript**: `npm install nemoflow`
"""

app = FastAPI(
    title="NemoFlow",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "NemoFlow", "url": "https://nemoflow.ai"},
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Request logging + timing
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


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def root():
    from app.landing import LANDING_HTML
    return LANDING_HTML


@app.get("/register", include_in_schema=False, response_class=HTMLResponse)
async def register_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NemoFlow — Get Your API Key</title>
<link rel="icon" href="https://nemoflow.ai/nemoflow-logo.webp" type="image/webp">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Poppins','Segoe UI',Arial,sans-serif;background:#0a0b10;color:#d4d8e8;min-height:100vh;display:flex;justify-content:center;align-items:center}
.card{max-width:440px;width:100%;margin:2rem;padding:2.5rem;background:#0f1118;border:1px solid #1c1f2e;border-radius:16px}
h1{font-size:1.5rem;font-weight:700;color:#f0f2f8;margin-bottom:0.4rem}
.sub{font-size:0.85rem;color:#9299b0;margin-bottom:2rem;line-height:1.5}
label{display:block;font-size:0.78rem;font-weight:500;color:#9299b0;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.05em}
input{width:100%;padding:0.75rem 1rem;background:#141620;border:1px solid #282c40;border-radius:8px;color:#f0f2f8;font-family:inherit;font-size:0.9rem;outline:none;transition:border-color 0.2s}
input:focus{border-color:#f07019}
input::placeholder{color:#5a5f75}
.btn{width:100%;padding:0.8rem;margin-top:1.25rem;background:#f07019;color:#fff;border:none;border-radius:8px;font-family:inherit;font-size:0.9rem;font-weight:700;cursor:pointer;transition:all 0.2s}
.btn:hover{background:#e0650f;box-shadow:0 0 30px rgba(240,112,25,0.2)}
.btn:disabled{opacity:0.5;cursor:not-allowed}
.result{display:none;margin-top:1.5rem;padding:1.25rem;background:#141620;border:1px solid #282c40;border-radius:10px}
.result h3{font-size:0.85rem;font-weight:600;color:#f07019;margin-bottom:0.5rem}
.key-box{font-family:'Fira Code',monospace;font-size:0.82rem;color:#f0f2f8;background:#0a0b10;padding:0.75rem 1rem;border-radius:6px;border:1px solid #282c40;word-break:break-all;margin-bottom:0.75rem;position:relative;cursor:pointer;transition:border-color 0.2s}
.key-box:hover{border-color:#f07019}
.key-box .copy-hint{position:absolute;right:0.75rem;top:50%;transform:translateY(-50%);font-size:0.65rem;color:#9299b0;font-family:'Poppins',sans-serif}
.warning{font-size:0.75rem;color:#f0c53b;line-height:1.5}
.error{display:none;margin-top:1rem;padding:0.75rem 1rem;background:rgba(240,90,90,0.08);border:1px solid rgba(240,90,90,0.2);border-radius:8px;font-size:0.82rem;color:#f05a5a}
.privacy{font-size:0.7rem;color:#6a6f85;margin-top:1rem;line-height:1.5;text-align:center}
.back{display:block;text-align:center;margin-top:1.5rem;font-size:0.8rem;color:#9299b0;text-decoration:none}
.back:hover{color:#f07019}
</style>
</head>
<body>
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
  </div>

  <p class="privacy">Your email is hashed for deduplication only — we never store it in plain text.</p>
  <a href="/" class="back">&larr; Back to NemoFlow</a>
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
    hint.style.color = '#f07019';
    setTimeout(function() { hint.textContent = 'click to copy'; hint.style.color = '#9299b0'; }, 2000);
  });
}
</script>
</body>
</html>"""


@app.get("/billing/success", include_in_schema=False, response_class=HTMLResponse)
async def billing_success():
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><title>NemoFlow — Payment Successful</title>
<style>body{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.card{text-align:center;max-width:480px;padding:3rem;background:#111;border:1px solid #222;border-radius:16px}
h1{color:#00d4ff;margin-bottom:1rem}p{color:#aaa;line-height:1.6}
a{color:#7b61ff;text-decoration:none}</style></head>
<body><div class="card"><h1>Welcome to Pro!</h1>
<p>Your API key has been upgraded to 10,000 daily calls. The change is effective immediately.</p>
<p style="margin-top:1.5rem"><a href="/docs">Go to API docs</a></p></div></body></html>"""


@app.get("/billing/cancel", include_in_schema=False, response_class=HTMLResponse)
async def billing_cancel():
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><title>NemoFlow — Checkout Cancelled</title>
<style>body{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.card{text-align:center;max-width:480px;padding:3rem;background:#111;border:1px solid #222;border-radius:16px}
h1{color:#ff6b9d;margin-bottom:1rem}p{color:#aaa;line-height:1.6}
a{color:#7b61ff;text-decoration:none}</style></head>
<body><div class="card"><h1>Checkout Cancelled</h1>
<p>No charges were made. You can upgrade anytime via the API.</p>
<p style="margin-top:1.5rem"><a href="/docs">Back to API docs</a></p></div></body></html>"""


@app.get("/health")
async def health():
    return {"status": "ok"}
