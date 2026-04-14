"""Import LLM tool assessments and merge them into the database.

Reads JSON files from data/assessments/, averages scores across LLMs,
and generates synthetic reports based on the consensus.

Usage:
    python -m app.import_assessments
    python -m app.import_assessments --dir data/assessments
"""

import argparse
import asyncio
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.categories import normalize_category
from app.core.security import make_fingerprint
from app.db.session import async_session
from app.models.tool import Tool
from app.models.report import ExecutionReport


def load_assessments(directory: str) -> list[dict]:
    """Load all JSON assessment files and merge by tool identifier."""
    path = Path(directory)
    all_tools: dict[str, list[dict]] = defaultdict(list)

    json_files = list(path.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {directory}")
        return []

    for file in json_files:
        print(f"Loading {file.name}...")
        try:
            data = json.loads(file.read_text())
            if not isinstance(data, list):
                print(f"  Skipping {file.name}: not a JSON array")
                continue
            for tool in data:
                identifier = tool.get("identifier", "").strip()
                if identifier:
                    all_tools[identifier].append(tool)
            print(f"  Loaded {len(data)} tools")
        except (json.JSONDecodeError, Exception) as e:
            print(f"  Error loading {file.name}: {e}")

    # Merge assessments by averaging scores
    merged = []
    for identifier, assessments in all_tools.items():
        reliability_scores = [a.get("reliability_estimate", 0.9) for a in assessments]
        latencies = [a.get("avg_latency_ms", 500) for a in assessments if a.get("avg_latency_ms")]

        # Use first assessment for metadata, average for scores
        base = assessments[0]
        merged_tool = {
            "identifier": identifier,
            "display_name": base.get("display_name", identifier),
            # Normalize at the merge step so every downstream writer
            # (seed + re-imports + LLM assessor) stores the same canonical
            # spelling. An unknown/empty category becomes "Other APIs".
            "category": normalize_category(base.get("category")) or "Other APIs",
            "reliability_estimate": sum(reliability_scores) / len(reliability_scores),
            "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 500,
            "common_errors": _merge_errors([a.get("common_errors", []) for a in assessments]),
            "pitfalls": _merge_strings([a.get("pitfalls", []) for a in assessments]),
            "mitigations": _merge_strings([a.get("mitigations", []) for a in assessments]),
            "sources": len(assessments),
        }
        merged.append(merged_tool)

    print(f"\nMerged into {len(merged)} unique tools from {len(json_files)} LLM sources")
    return merged


def _merge_errors(error_lists: list[list[dict]]) -> list[dict]:
    """Average error frequencies across LLM assessments."""
    counts: dict[str, list[float]] = defaultdict(list)
    for errors in error_lists:
        for err in errors:
            cat = err.get("category", "")
            freq = err.get("frequency", 0)
            if cat:
                counts[cat].append(freq)

    merged = []
    for cat, freqs in counts.items():
        merged.append({"category": cat, "frequency": sum(freqs) / len(freqs)})

    # Normalize to sum to 1.0
    total = sum(e["frequency"] for e in merged)
    if total > 0:
        for e in merged:
            e["frequency"] = round(e["frequency"] / total, 3)

    return sorted(merged, key=lambda x: x["frequency"], reverse=True)


def _merge_strings(string_lists: list[list[str]]) -> list[str]:
    """Deduplicate and take top strings."""
    seen = set()
    result = []
    for strings in string_lists:
        for s in strings:
            normalized = s.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                result.append(s.strip())
    return result[:5]  # Top 5


async def import_to_db(tools: list[dict]):
    """Import merged assessments into the database as synthetic reports."""
    now = datetime.now(timezone.utc)
    fingerprint = make_fingerprint("llm_consensus", "llm_consensus")
    created = 0
    updated = 0
    reports_created = 0

    async with async_session() as db:
        for tool_data in tools:
            identifier = tool_data["identifier"]
            reliability = tool_data["reliability_estimate"]
            avg_latency = tool_data["avg_latency_ms"]
            errors = tool_data["common_errors"]

            # Upsert tool
            result = await db.execute(select(Tool).where(Tool.identifier == identifier))
            tool = result.scalar_one_or_none()

            if tool:
                tool.display_name = tool_data["display_name"]
                tool.category = tool_data["category"]
                updated += 1
            else:
                tool = Tool(
                    identifier=identifier,
                    display_name=tool_data["display_name"],
                    category=tool_data["category"],
                )
                db.add(tool)
                created += 1

            await db.flush()

            # Check if we already have enough reports for this tool
            if tool.report_count >= 50:
                continue

            # Generate synthetic reports based on LLM consensus
            num_reports = random.randint(80, 150)
            for i in range(num_reports):
                age_days = random.uniform(0, 30)
                created_at = now - timedelta(days=age_days)
                success = random.random() < reliability
                latency = max(30, int(random.gauss(avg_latency, avg_latency * 0.3)))

                error_category = None
                if not success and errors:
                    r = random.random()
                    cumulative = 0.0
                    for err in errors:
                        cumulative += err["frequency"]
                        if r <= cumulative:
                            error_category = err["category"]
                            break
                    if not error_category:
                        error_category = errors[-1]["category"]

                report = ExecutionReport(
                    tool_id=tool.id,
                    success=success,
                    error_category=error_category,
                    latency_ms=latency,
                    context_hash="__global__",
                    reporter_fingerprint=fingerprint,
                    data_pool=None,
                    created_at=created_at,
                )
                db.add(report)
                reports_created += 1

            # Accumulate so re-imports don't clobber earlier counts — scoring
            # reads rows directly, but report_count drives sort order for
            # alternatives and discovery, so it has to reflect the true total.
            tool.report_count = (tool.report_count or 0) + num_reports

        await db.commit()

    print(f"\nImport complete:")
    print(f"  Tools created: {created}")
    print(f"  Tools updated: {updated}")
    print(f"  Reports generated: {reports_created}")


async def main(directory: str):
    tools = load_assessments(directory)
    if not tools:
        return
    await import_to_db(tools)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import LLM tool assessments")
    parser.add_argument("--dir", default="data/assessments", help="Directory with JSON assessment files")
    args = parser.parse_args()
    asyncio.run(main(args.dir))
