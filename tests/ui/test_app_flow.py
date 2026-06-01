from __future__ import annotations

import os

import pytest
import pytest_asyncio
from agents.orchestrator import OzStartupFinderPipeline
from google.adk.sessions import InMemorySessionService


@pytest.fixture(scope="module")
def pipeline_factory():
    session_service = InMemorySessionService()
    counter = {"n": 0}

    def build():
        counter["n"] += 1
        return OzStartupFinderPipeline(
            session_id=f"oz-startup-finder:pytest:{counter['n']}",
        )

    return build


@pytest.mark.asyncio
async def test_orchestrator_reaches_synthesis(pipeline_factory):
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY required for orchestrator integration test")
    pipeline = pipeline_factory()
    state = await pipeline.run("Find Melbourne-based code review tools")

    assert state.user_query == "Find Melbourne-based code review tools"
    assert state.synthesis is not None
    summary = state.synthesis.get("summary")
    assert summary is not None
    leads = state.synthesis.get("leads_json") or []
    assert isinstance(leads, list)
    if leads:
        first = leads[0]
        assert "company_name" in first
        assert "relevance_narrative" in first
        assert "confidence" in first
