from __future__ import annotations

from dataclasses import dataclass, field

from agents.clarifying.agent import build_clarifying_agent
from agents.enricher.agent import build_enricher_agent
from agents.retriever.agent import build_retriever_agent
from agents.router.agent import build_router_agent
from agents.scorer.agent import build_scorer_agent
from agents.synthesizer.agent import build_synthesizer_agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService


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
    await session_service.create_session(session_id=session_id, app_name="oz-startup-finder", user_id="local-user")


async def _consume(runner: Runner, *, user_id: str, session_id: str, new_message: str):
    await _create_session(runner.session_service, session_id)
    latest = None
    payload = {"role": "user", "parts": [{"text": new_message}]}
    for event in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=payload,
    ):
        latest = event
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

        clarifying_session = Runner(
            agent=self.clarifying_agent,
            session_service=self.session_service,
            app_name="oz-startup-finder",
        )
        clarifying_out = await _consume(
            clarifying_session,
            user_id="local-user",
            session_id=f"{self.session_id}:clarifying",
            new_message=user_query,
        )
        self._assign("clarifying_questions", getattr(clarifying_out, "follow_up_questions", []))
        if self._needs_clarification():
            return self.state

        router_session = Runner(
            agent=self.router_agent,
            session_service=self.session_service,
            app_name="oz-startup-finder",
        )
        router_out = await _consume(
            router_session,
            user_id="local-user",
            session_id=f"{self.session_id}:router",
            new_message=user_query,
        )
        self._assign("router_output", getattr(router_out, "structured_output", {}))

        retriever_session = Runner(
            agent=self.retriever_agent,
            session_service=self.session_service,
            app_name="oz-startup-finder",
        )
        retrieval_out = await _consume(
            retriever_session,
            user_id="local-user",
            session_id=f"{self.session_id}:retriever",
            new_message=user_query,
        )
        self._assign("retrieved_candidates", getattr(retrieval_out, "top_matches", []))

        enriched: list[dict] = []
        for candidate in self.state.retrieved_candidates[:10]:
            enriched_session = Runner(
                agent=self.enricher_agent,
                session_service=self.session_service,
                app_name="oz-startup-finder",
            )
            enriched_out = await _consume(
                enriched_session,
                user_id="local-user",
                session_id=f"{self.session_id}:enricher:{candidate.get('company_name', 'unknown')}",
                new_message=user_query,
            )
            payload = getattr(enriched_out, "structured_output", {})
            payload.setdefault("company_name", candidate.get("company_name"))
            enriched.append(payload)
        self._assign("enriched_leads", enriched)

        scorer_session = Runner(
            agent=self.scorer_agent,
            session_service=self.session_service,
            app_name="oz-startup-finder",
        )
        scorer_out = await _consume(
            scorer_session,
            user_id="local-user",
            session_id=f"{self.session_id}:scorer",
            new_message=user_query,
        )
        self._assign("scored_leads", getattr(scorer_out, "scored_leads", []))

        synthesizer_session = Runner(
            agent=self.synthesizer_agent,
            session_service=self.session_service,
            app_name="oz-startup-finder",
        )
        synthesizer_out = await _consume(
            synthesizer_session,
            user_id="local-user",
            session_id=f"{self.session_id}:synthesizer",
            new_message=user_query,
        )
        self._assign("synthesis", getattr(synthesizer_out, "structured_output", {}))

        return self.state

    def _needs_clarification(self) -> bool:
        return bool(self.state.clarifying_questions)

    def _assign(self, field_name: str, value: object) -> None:
        object.__setattr__(self.state, field_name, value)
