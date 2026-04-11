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
