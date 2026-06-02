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
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )
    query = "Melbourne Fintech"
    pipeline = OzStartupFinderPipeline(session_id="retriever-debug")
    state = await pipeline.run(query)
    print("USER_QUERY=" + _safe_json(query))
    print("ROUTER_STRATEGY=" + _safe_json(state.router_output))
    print("RETRIEVER_RAW_TEXT_START")
    print(getattr(state, 'retrieval_raw_text', '') or '')
    print("RETRIEVER_RAW_TEXT_END")
    print("RETRIEVED_CANDIDATES=" + _safe_json(state.retrieved_candidates))
    print("ENRICHED_LEADS=" + _safe_json(state.enriched_leads))
    print("SCORED_LEADS=" + _safe_json(state.scored_leads))
    print("FINAL_SUMMARY=" + _safe_json(state.synthesis))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
