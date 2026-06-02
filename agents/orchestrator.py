from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

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


def _text_from_event(event: Any) -> str:
    try:
        content = getattr(event, "content", None)
        if content is None:
            return ""
        parts = getattr(content, "parts", None) or []
        texts = []
        for part in parts:
            value = getattr(part, "text", None)
            if value:
                texts.append(value)
        return "\n".join(texts).strip()
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Failed to extract text from event: %s", exc)
        return ""


def _json_from_event_text(event: Any) -> Any:
    raw = _text_from_event(event)
    if not raw:
        return {}
    try:
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if "\n" in stripped:
                stripped = stripped.split("\n", 1)[1]
                if stripped.endswith("```"):
                    stripped = stripped[:-3]
            stripped = stripped.strip()
        return json.loads(stripped)
    except Exception as exc:  # pragma: no cover - best effort parsing
        logger.debug("Failed to parse JSON from event text: %s\n%s", exc, raw)
        return {}


def _assign(state: PipelineState, field_name: str, value: Any) -> None:
    try:
        object.__setattr__(state, field_name, value)
    except Exception as exc:
        logger.debug("Failed to assign %s: %s", field_name, exc)


async def _consume(runner: Runner, *, user_id: str, session_id: str, new_message: str, label: str) -> Any:
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
        self.state = PipelineState(user_query=user_query)
        logger.info("Pipeline start query=%s", user_query)

        clarifying_event = await _consume(
            Runner(agent=self.clarifying_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:clarifying",
            new_message=user_query,
            label="clarifying",
        )
        clarifying_json = _json_from_event_text(clarifying_event)
        clarifying_text = _text_from_event(clarifying_event)
        questions = clarifying_json.get("questions") or clarifying_json.get("follow_up_questions") or []
        if isinstance(questions, str):
            questions = [questions]
        _assign(self.state, "clarifying_questions", [str(item) for item in questions])

        router_event = await _consume(
            Runner(agent=self.router_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:router",
            new_message=user_query,
            label="router",
        )
        router_json = _json_from_event_text(router_event)
        _assign(self.state, "router_output", router_json if isinstance(router_json, dict) else {})

        retrieval_event = await _consume(
            Runner(agent=self.retriever_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:retriever",
            new_message=user_query,
            label="retriever",
        )
        retrieval_json = _json_from_event_text(retrieval_event)
        retrieved = retrieval_json.get("top_matches") if isinstance(retrieval_json, dict) else None
        _assign(self.state, "retrieved_candidates", retrieved or [])

        if not self.state.retrieved_candidates:
            logger.info("No retrieval candidates; skipping enrichment/scoring/synthesis.")
            logger.info("Pipeline incomplete: retrieval returned no candidates")
            return self.state

        enriched: list[dict] = []
        for idx, candidate in enumerate(self.state.retrieved_candidates[:10], start=1):
            label = f"enricher:{idx}"
            enriched_event = await _consume(
                Runner(agent=self.enricher_agent, session_service=self.session_service, app_name="oz-startup-finder"),
                user_id="local-user",
                session_id=f"{self.session_id}:enricher:{candidate.get('company_name', 'unknown')}",
                new_message=user_query,
                label=label,
            )
            enriched_json = _json_from_event_text(enriched_event)
            payload = enriched_json if isinstance(enriched_json, dict) else {}
            payload.setdefault("company_name", candidate.get("company_name"))
            enriched.append(payload)
        _assign(self.state, "enriched_leads", enriched)

        scorer_event = await _consume(
            Runner(agent=self.scorer_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:scorer",
            new_message=user_query,
            label="scorer",
        )
        scorer_json = _json_from_event_text(scorer_event)
        _assign(self.state, "scored_leads", (scorer_json.get("scored_leads") or []) if isinstance(scorer_json, dict) else [])

        synthesizer_event = await _consume(
            Runner(agent=self.synthesizer_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:synthesizer",
            new_message=user_query,
            label="synthesizer",
        )
        synthesizer_json = _json_from_event_text(synthesizer_event)
        _assign(self.state, "synthesis", synthesizer_json if isinstance(synthesizer_json, dict) else {})

        logger.info("Pipeline complete")
        return self.state
