import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.schemas.assess import AssessResponse, AlternativeTool


def _cache_key(tool_id: str, context_hash: str, data_pool: str | None) -> str:
    return f"score:{tool_id}:{context_hash}:{data_pool or ''}"


async def get_cached_score(
    redis: Redis, tool_id: str, context_hash: str, data_pool: str | None
) -> AssessResponse | None:
    key = _cache_key(tool_id, context_hash, data_pool)
    data = await redis.get(key)
    if data is None:
        return None
    parsed = json.loads(data)
    return AssessResponse(
        reliability_score=parsed["reliability_score"],
        confidence=parsed["confidence"],
        historical_success_rate=parsed["historical_success_rate"],
        predicted_failure_risk=parsed["predicted_failure_risk"],
        common_pitfalls=parsed["common_pitfalls"],
        recommended_mitigations=parsed["recommended_mitigations"],
        top_alternatives=[AlternativeTool(**a) for a in parsed["top_alternatives"]],
        estimated_latency_ms=parsed.get("estimated_latency_ms"),
        last_updated=datetime.fromisoformat(parsed["last_updated"]),
    )


async def set_cached_score(
    redis: Redis,
    tool_id: str,
    context_hash: str,
    data_pool: str | None,
    response: AssessResponse,
    ttl: int,
) -> None:
    key = _cache_key(tool_id, context_hash, data_pool)
    data = {
        "reliability_score": response.reliability_score,
        "confidence": response.confidence,
        "historical_success_rate": response.historical_success_rate,
        "predicted_failure_risk": response.predicted_failure_risk,
        "common_pitfalls": response.common_pitfalls,
        "recommended_mitigations": response.recommended_mitigations,
        "top_alternatives": [a.model_dump() for a in response.top_alternatives],
        "estimated_latency_ms": response.estimated_latency_ms,
        "last_updated": response.last_updated.isoformat(),
    }
    await redis.set(key, json.dumps(data), ex=ttl)
