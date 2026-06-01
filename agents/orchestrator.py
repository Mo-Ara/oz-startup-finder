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
            session_id=f"{self.session_id}:clarifying",
        )
        clarifying_out = await clarifying_session.run(user_query)
        self._assign("clarifying_questions", getattr(clarifying_out, "follow_up_questions", []))
        if self._needs_clarification():
            return self.state

        router_session = Runner(
            agent=self.router_agent,
            session_service=self.session_service,
            session_id=f"{self.session_id}:router",
        )
        router_out = await router_session.run(user_query)
        self._assign("router_output", getattr(router_out, "structured_output", {}))

        retriever_session = Runner(
            agent=self.retriever_agent,
            session_service=self.session_service,
            session_id=f"{self.session_id}:retriever",
        )
        retrieval_out = await retriever_session.run(user_query)
        self._assign("retrieved_candidates", getattr(retrieval_out, "top_matches", []))

        enriched: list[dict] = []
        for candidate in self.state.retrieved_candidates[:10]:
            enriched_session = Runner(
                agent=self.enricher_agent,
                session_service=self.session_service,
                session_id=f"{self.session_id}:enricher:{candidate.get('company_name', 'unknown')}",
            )
            enriched_out = await enriched_session.run(user_query)
            payload = getattr(enriched_out, "structured_output", {})
            payload.setdefault("company_name", candidate.get("company_name"))
            enriched.append(payload)
        self._assign("enriched_leads", enriched)

        scorer_session = Runner(
            agent_name=self.scorer_agent.name,
            agent=self.scorer_agent,
            session_service=self.session_service,
            session_id=f"{self.session_id}:scorer",
        )
        scorer_out = await scorer_session.run(user_query)
        self._assign("scored_leads", getattr(scorer_out, "scored_leads", []))

        synthesizer_session = Runner(
            agent_name=self.synthesizer_agent.name,
            agent=self.synthesizer_agent,
            session_service=self.session_service,
            session_id=f"{self.session_id}:synthesizer",
        )
        synthesizer_out = await synthesizer_session.run(user_query)
        self._assign("synthesis", getattr(synthesizer_out, "structured_output", {}))

        return self.state

    def _needs_clarification(self) -> bool:
        return bool(self.state.clarifying_questions)

    def _assign(self, field_name: str, value: object) -> None:
        object.__setattr__(self.state, field_name, value)
