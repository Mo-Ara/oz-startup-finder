from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.orchestrator import OzStartupFinderPipeline


FIXTURE_DB = Path(__file__).resolve().parent.parent / "data" / "startups.db"


@pytest.fixture()
def pipeline() -> OzStartupFinderPipeline:
    instance = OzStartupFinderPipeline(session_id="unit-test-retriever")
    instance.session_service = instance.session_service  # default in-memory service
    return instance


def test_coercion_handles_results_key(pipeline: OzStartupFinderPipeline) -> None:
    payload = json.dumps({"results": [{"company_name": "A"}]})
    assert pipeline._coerce_retrieval_output(payload) == {"results": [{"company_name": "A"}]}


def test_coercion_handles_top_matches_key(pipeline: OzStartupFinderPipeline) -> None:
    payload = json.dumps({"top_matches": [{"company_name": "B"}]})
    assert pipeline._coerce_retrieval_output(payload) == {"top_matches": [{"company_name": "B"}]}


def test_coercion_skips_json_fences(pipeline: OzStartupFinderPipeline) -> None:
    payload = "```json\n" + json.dumps({"results": [{"company_name": "C"}]}) + "\n```"
    assert pipeline._coerce_retrieval_output(payload) == {"results": [{"company_name": "C"}]}


def test_coercion_ignores_surrounding_text(pipeline: OzStartupFinderPipeline) -> None:
    bad_json = "Here are the results:\n" + json.dumps({"results": [{"company_name": "D"}]}) + " Hope that helps!"
    assert pipeline._coerce_retrieval_output(bad_json) == {"results": [{"company_name": "D"}]}


def test_normalize_scorer_output_maps_flat_scoring_values(
    pipeline: OzStartupFinderPipeline,
) -> None:
    normalized = pipeline._normalize_scorer_output({
        "company_name": "FlatCo",
        "relevance_score": 85,
        "confidence_score": 88,
        "fit_reason": "Strong fit.",
    })
    assert normalized[0]["company_name"] == "FlatCo"
    assert normalized[0]["confidence_score"] == 88


def test_normalize_scorer_output_maps_leads_key(pipeline: OzStartupFinderPipeline) -> None:
    normalized = pipeline._normalize_scorer_output({
        "leads": [
            {"company_name": "Company X", "relevance_score": 90, "confidence_score": 92}
        ]
    })
    assert len(normalized) == 1
    assert normalized[0]["company_name"] == "Company X"


def test_fallback_synthesis_uses_enriched_when_scored_missing(
    pipeline: OzStartupFinderPipeline,
) -> None:
    pipeline.state.enriched_leads = [
        {
            "company_name": "Fallback Inc",
            "industry": "fintech",
            "company_city": "Melbourne",
            "match_score": 55,
        }
    ]
    pipeline.state.scored_leads = []
    pipeline.state.retrieved_candidates = []
    result = pipeline._fallback_synthesis(pipeline.state)
    assert result["leads_json"]
    assert result["leads_json"][0]["company_name"] == "Fallback Inc"


@pytest.mark.skipif(not FIXTURE_DB.exists(), reason="fixture db not built yet")
def test_retriever_contract_finds_melbourne_fintech(
    pipeline: OzStartupFinderPipeline,
) -> None:
    pipeline.state.user_query = "melbourne fintech"
    pipeline._apply_db_search_state(query="melbourne fintech", strategy="market_scan")

    assert len(pipeline.state.retrieved_candidates) >= 1
    names = [row["company_name"] for row in pipeline.state.retrieved_candidates]
    assert "QuantumLedger" in names, "expected Melbourne fintech candidate from DB"
