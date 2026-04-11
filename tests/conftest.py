import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base
from app.models.tool import Tool
from app.models.report import ExecutionReport
from app.models.api_key import ApiKey
from app.core.security import generate_api_key


# Use in-memory SQLite for tests — override the DB URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///test.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def sample_tool(db_session):
    tool = Tool(
        id=uuid.uuid4(),
        identifier="https://api.example.com/v1/test",
        display_name="Test API",
        category="test",
        report_count=0,
    )
    db_session.add(tool)
    await db_session.commit()
    return tool


@pytest_asyncio.fixture
async def tool_with_reports(db_session, sample_tool):
    """Create a tool with 20 reports: 16 success, 4 failure over 14 days."""
    now = datetime.now(timezone.utc)
    for i in range(20):
        age = timedelta(days=i * 0.7)  # Spread over ~14 days
        success = i >= 4  # First 4 are failures, rest are successes
        report = ExecutionReport(
            tool_id=sample_tool.id,
            success=success,
            error_category=None if success else "timeout",
            latency_ms=200 + i * 10,
            context_hash="__global__",
            reporter_fingerprint="test_fp",
            created_at=now - age,
        )
        db_session.add(report)

    sample_tool.report_count = 20
    await db_session.commit()
    return sample_tool


@pytest_asyncio.fixture
async def api_key_record(db_session):
    full_key, key_hash, key_prefix = generate_api_key()
    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        tier="pro",
        daily_limit=10000,
    )
    db_session.add(api_key)
    await db_session.commit()
    return full_key, api_key
