from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from agents.orchestrator import OzStartupFinderPipeline


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception as exc:  # pragma: no cover - defensive
        return f"<non-serializable: {exc}>"


async def _run() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )
    query = "Melbourne Fintech"
    pipeline = OzStartupFinderPipeline(session_id="system-test")
    state = await pipeline.run(query)
    print("FINAL_SUMMARY=" + _safe_json(state.synthesis))
    print("ENRICHED_LEADS=" + _safe_json(state.enriched_leads))
    print("SCORED_LEADS=" + _safe_json(state.scored_leads))
    print("RETRIEVED_CANDIDATES=" + _safe_json(state.retrieved_candidates))
    if state.retrieved_candidates:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
