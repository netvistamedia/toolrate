from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from app.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = aioredis.from_url(
        settings.redis_url, decode_responses=True, max_connections=50
    )
    yield
    # Shutdown
    await app.state.redis.close()
    await engine.dispose()


app = FastAPI(
    title="NemoFlow",
    description="Reliability oracle for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)


from app.api.v1.router import router as v1_router  # noqa: E402

app.include_router(v1_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
