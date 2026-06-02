from __future__ import annotations

import json
import logging

import pytest

from agents.orchestrator import OzStartupFinderPipeline


def _safe_json(value):
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception as exc:  # pragma: no cover - defensive
        return f"<non-serializable: {exc}>"


@pytest.mark.asyncio
async def test_melbourne_fintech_pipeline(caplog):
    caplog.set_level(logging.INFO)
    query = "melbourne fintech"
    pipeline = OzStartupFinderPipeline(session_id="system-test")
    state = await pipeline.run(query)

    logging.getLogger("oz.startup.finder.system").info(
        "FINAL_SUMMARY=%s", _safe_json(state.synthesis)
    )
    logging.getLogger("oz.startup.finder.system").info(
        "SCORED_LEADS=%s", _safe_json(state.scored_leads)
    )
    logging.getLogger("oz.startup.finder.system").info(
        "RETRIEVED_CANDIDATES=%s", _safe_json(state.retrieved_candidates)
    )

    assert state.retrieved_candidates, "retrieval must return candidates"
    assert state.enriched_leads or state.scored_leads, "enrichment or scoring must produce leads"
    assert state.synthesis.get("leads_json"), "synthesis must include leads_json"
