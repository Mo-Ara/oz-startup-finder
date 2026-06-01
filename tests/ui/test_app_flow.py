from __future__ import annotations

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
