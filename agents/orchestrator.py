from __future__ import annotations

import logging
from dataclasses import dataclass, field

from agents.clarifying.agent import build_clarifying_agent
from agents.enricher.agent import build_enricher_agent
from agents.retriever.agent import build_retriever_agent
from agents.router.agent import build_router_agent
from agents.scorer.agent import build_scorer_agent
from agents.synthesizer.agent import build_synthesizer_agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)


@dataclass
class PipelineState:
    user_query: str = ""
    clarifying_questions: list[str] = field(default_factory=list)
    router_output: dict = field(default_factory=dict)
    retrieved_candidates: list[dict] = field(default_factory=list)
    enriched_leads: list[dict] = field(default_factory=list)
    scored_leads: list[dict] = field(default_factory=list)
    synthesis: dict = field(default_factory=dict)


async def _create_session(session_service: InMemorySessionService, session_id: str) -> None:
    logger.info("Creating session: %s", session_id)
    await session_service.create_session(session_id=session_id, app_name="oz-startup-finder", user_id="local-user")


async def _consume(runner: Runner, *, user_id: str, session_id: str, new_message: str, label: str):
    await _create_session(runner.session_service, session_id)
    content = types.Content(
        role="user",
        parts=[types.Part(text=new_message)],
    )
    latest = None
    event_count = 0
    logger.info("Stage %s: start session=%s", label, session_id)
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            event_count += 1
            latest = event
    except Exception as exc:
        logger.error("Stage %s failed in session=%s: %s", label, session_id, exc, exc_info=True)
        raise RuntimeError(f"Stage '{label}' failed in session '{session_id}': {exc}") from exc

    logger.info(
        "Stage %s: complete session=%s events=%s latest=%s",
        label,
        session_id,
        event_count,
        getattr(latest, "__class__", type(latest)).__name__,
    )
    return latest


class OzStartupFinderPipeline:
    def __init__(self, session_id: str | None = None, model: str | None = None) -> None:
        self.model = model
        self.session_service = InMemorySessionService()
        self.session_id = session_id or "oz-startup-finder"
        self.state = PipelineState()

        self.clarifying_agent = build_clarifying_agent(model=self.model)
        self.router_agent = build_router_agent(model=self.model)
        self.retriever_agent = build_retriever_agent(model=self.model)
        self.enricher_agent = build_enricher_agent(model=self.model)
        self.scorer_agent = build_scorer_agent(model=self.model)
        self.synthesizer_agent = build_synthesizer_agent(model=self.model)

    async def run(self, user_query: str) -> PipelineState:
        self.state.user_query = user_query

        logger.info("Pipeline start query=%s", user_query)

        clarifying_out = await _consume(
            Runner(agent=self.clarifying_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:clarifying",
            new_message=user_query,
            label="clarifying",
        )
        self._assign("clarifying_questions", getattr(clarifying_out, "follow_up_questions", []))
        if self._needs_clarification():
            logger.info("Clarification required; pipeline paused for user input.")
            return self.state

        router_out = await _consume(
            Runner(agent=self.router_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:router",
            new_message=user_query,
            label="router",
        )
        self._assign("router_output", getattr(router_out, "structured_output", {}))

        retrieval_out = await _consume(
            Runner(agent=self.retriever_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:retriever",
            new_message=user_query,
            label="retriever",
        )
        self._assign("retrieved_candidates", getattr(retrieval_out, "top_matches", []))

        enriched: list[dict] = []
        for idx, candidate in enumerate(self.state.retrieved_candidates[:10], start=1):
            label = f"enricher:{idx}"
            enriched_out = await _consume(
                Runner(agent=self.enricher_agent, session_service=self.session_service, app_name="oz-startup-finder"),
                user_id="local-user",
                session_id=f"{self.session_id}:enricher:{candidate.get('company_name', 'unknown')}",
                new_message=user_query,
                label=label,
            )
            payload = getattr(enriched_out, "structured_output", {})
            payload.setdefault("company_name", candidate.get("company_name"))
            enriched.append(payload)
        self._assign("enriched_leads", enriched)

        scorer_out = await _consume(
            Runner(agent=self.scorer_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:scorer",
            new_message=user_query,
            label="scorer",
        )
        self._assign("scored_leads", getattr(scorer_out, "scored_leads", []))

        synthesizer_out = await _consume(
            Runner(agent=self.synthesizer_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:synthesizer",
            new_message=user_query,
            label="synthesizer",
        )
        self._assign("synthesis", getattr(synthesizer_out, "structured_output", {}))

        logger.info("Pipeline complete")
        return self.state

    def _needs_clarification(self) -> bool:
        return bool(self.state.clarifying_questions)

    def _assign(self, field_name: str, value: object) -> None:
        object.__setattr__(self.state, field_name, value)
