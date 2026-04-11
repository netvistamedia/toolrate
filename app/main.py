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
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NemoFlow — Reliability Oracle for AI Agents</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem}
.container{max-width:720px;text-align:center}
h1{font-size:3rem;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b61ff,#ff6b9d);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.5rem}
.tagline{font-size:1.25rem;color:#888;margin-bottom:2.5rem}
.stats{display:flex;gap:2rem;justify-content:center;margin-bottom:2.5rem;flex-wrap:wrap}
.stat{background:#151515;border:1px solid #222;border-radius:12px;padding:1.25rem 1.5rem;min-width:140px}
.stat-value{font-size:2rem;font-weight:700;color:#00d4ff}
.stat-label{font-size:.8rem;color:#666;margin-top:.25rem;text-transform:uppercase;letter-spacing:.05em}
.code{background:#151515;border:1px solid #222;border-radius:12px;padding:1.5rem;text-align:left;margin-bottom:2rem;overflow-x:auto}
.code pre{font-family:'SF Mono',Menlo,monospace;font-size:.85rem;color:#ccc;line-height:1.6}
.code .kw{color:#7b61ff}.code .fn{color:#00d4ff}.code .str{color:#ff6b9d}.code .cm{color:#555}
.buttons{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:2rem}
a.btn{display:inline-block;padding:.75rem 1.5rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.95rem;transition:all .2s}
.btn-primary{background:linear-gradient(135deg,#00d4ff,#7b61ff);color:#fff}
.btn-primary:hover{opacity:.9;transform:translateY(-1px)}
.btn-secondary{background:#1a1a1a;border:1px solid #333;color:#ccc}
.btn-secondary:hover{border-color:#555;color:#fff}
.features{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:2rem;text-align:left}
.feature{background:#151515;border:1px solid #222;border-radius:10px;padding:1rem 1.25rem}
.feature h3{font-size:.9rem;color:#00d4ff;margin-bottom:.25rem}
.feature p{font-size:.8rem;color:#888;line-height:1.4}
.footer{color:#444;font-size:.75rem;margin-top:1rem}
@media(max-width:600px){h1{font-size:2rem}.stats{flex-direction:column;align-items:center}.features{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="container">
<h1>NemoFlow</h1>
<p class="tagline">The reliability oracle for AI agents</p>

<div class="stats">
<div class="stat"><div class="stat-value">600+</div><div class="stat-label">Tools Tracked</div></div>
<div class="stat"><div class="stat-value">68K+</div><div class="stat-label">Reports</div></div>
<div class="stat"><div class="stat-value">&lt;10ms</div><div class="stat-label">Cache Hit</div></div>
<div class="stat"><div class="stat-value">9</div><div class="stat-label">LLM Sources</div></div>
</div>

<div class="code"><pre><span class="kw">from</span> nemoflow <span class="kw">import</span> NemoFlowClient, guard

client = NemoFlowClient(<span class="str">"nf_live_..."</span>)

<span class="cm"># One line — assess, execute, report, auto-fallback</span>
result = <span class="fn">guard</span>(client, <span class="str">"https://api.openai.com/v1/chat/completions"</span>,
               <span class="kw">lambda</span>: openai.chat.completions.create(...))</pre></div>

<div class="buttons">
<a href="/docs" class="btn btn-primary">API Docs</a>
<a href="https://github.com/netvistamedia/nemoflow" class="btn btn-secondary">GitHub</a>
</div>

<div class="features">
<div class="feature"><h3>Assess Before Calling</h3><p>Real-time reliability scores, failure risk, pitfalls, and mitigations for 600+ tools</p></div>
<div class="feature"><h3>Auto-Fallback</h3><p>guard() tries alternatives automatically when a tool fails or scores too low</p></div>
<div class="feature"><h3>Hidden Gems</h3><p>Discover underrated tools that agents switch to after popular tools fail</p></div>
<div class="feature"><h3>Data Moat</h3><p>Every report makes scores more accurate. 9 LLM sources + live agent data</p></div>
</div>

<p class="footer">Built for agents, by agents. GDPR compliant. Hosted in Germany.</p>
</div>
</body>
</html>"""


@app.get("/health")
async def health():
    return {"status": "ok"}
