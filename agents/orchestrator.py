from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
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
from shared.data_loader import search_companies

logger = logging.getLogger(__name__)


@dataclass
class PipelineState:
    user_query: str = ""
    clarifying_questions: list[str] = field(default_factory=list)
    router_output: dict = field(default_factory=dict)
    retrieved_candidates: list[dict] = field(default_factory=list)
    retrieval_raw_text: str = ""
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
        router_output = router_json if isinstance(router_json, dict) else {}
        self.state.router_output = router_output

        strategy = router_output.get("strategy") if isinstance(router_output, dict) else None
        if not strategy:
            strategy = "market_scan"

        retrieval_query = user_query
        if strategy == "company_lookup":
            company_hint = clarifying_text or user_query
            retrieval_query = company_hint
        elif strategy == "competitor_research":
            retrieval_query = user_query.split("competitor")[0].strip() or user_query

        retrieval_input = json.dumps(
            {"query": retrieval_query, "strategy": strategy},
            ensure_ascii=False,
        )

        retrieval_event = await _consume(
            Runner(agent=self.retriever_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:retriever",
            new_message=retrieval_input,
            label="retriever",
        )
        retrieval_text = _text_from_event(retrieval_event)
        self.state.retrieval_raw_text = retrieval_text

        retrieval_json = self._coerce_retrieval_output(retrieval_text)
        if retrieval_json is None:
            retrieval_json = {}
        retrieved = (
            retrieval_json.get("top_matches")
            or retrieval_json.get("results")
            or retrieval_json.get("candidates")
            or []
        )
        self.state.retrieved_candidates = retrieved or []

        if not self.state.retrieved_candidates:
            logger.info("No retrieval candidates found for query=%s", user_query)
            self._apply_db_search_state(query=user_query, strategy=strategy)
            retrieved = self.state.retrieved_candidates
            if not retrieved:
                return self.state

        # Normalize each retrieved candidate so downstream agents always see
        # consistent fields (company_name, industry, company_city, match_score, rationale).
        self.state.retrieved_candidates = [
            {
                "company_name": item.get("company_name"),
                "industry": item.get("industry"),
                "company_city": item.get("company_city"),
                "match_score": item.get("match_score") or item.get("score") or 0,
                "rationale": item.get("rationale") or item.get("reason") or item.get("fit_reason") or "",
            }
            for item in self.state.retrieved_candidates
            if item.get("company_name")
        ]
        if not self.state.retrieved_candidates:
            logger.info("No normalized retrieval candidates for query=%s", user_query)
            self._apply_db_search_state(query=user_query, strategy=strategy)

        self.state.enriched_leads = []
        for idx, candidate in enumerate(self.state.retrieved_candidates[:10], start=1):
            label = f"enricher:{idx}"
            enrichment_input = json.dumps(
                {
                    "company": candidate,
                    "query": user_query,
                    "strategy": strategy,
                    "router_output": self.state.router_output,
                },
                ensure_ascii=False,
            )
            enriched_event = await _consume(
                Runner(agent=self.enricher_agent, session_service=self.session_service, app_name="oz-startup-finder"),
                user_id="local-user",
                session_id=f"{self.session_id}:enricher:{candidate.get('company_name', 'unknown')}",
                new_message=enrichment_input,
                label=label,
            )
            enriched_json = _json_from_event_text(enriched_event)
            payload = enriched_json if isinstance(enriched_json, dict) else {}
            payload.setdefault("company_name", candidate.get("company_name"))
            self.state.enriched_leads.append(payload)

        scorer_input = json.dumps(
            {
                "enriched_leads": self.state.enriched_leads,
                "query": user_query,
                "strategy": strategy,
            },
            ensure_ascii=False,
        )

        self.state.scored_leads = []
        scorer_event = await _consume(
            Runner(agent=self.scorer_agent, session_service=self.session_service, app_name="oz-startup-finder"),
            user_id="local-user",
            session_id=f"{self.session_id}:scorer",
            new_message=scorer_input,
            label="scorer",
        )
        scorer_json = _json_from_event_text(scorer_event)
        if isinstance(scorer_json, dict):
            scored = scorer_json.get("scored_leads") or scorer_json.get("leads") or []
            if not scored and "score" in scorer_json:
                scored = self._normalize_scorer_output(scorer_json)
            self.state.scored_leads = scored or self.state.enriched_leads

        self.state.synthesis = {}
        synthesis_input_payload = None
        if self.state.scored_leads:
            synthesis_input_payload = {
                "scored_leads": self.state.scored_leads,
                "query": user_query,
                "strategy": strategy,
            }
        elif self.state.enriched_leads:
            synthesis_input_payload = {
                "scored_leads": self.state.enriched_leads,
                "query": user_query,
                "strategy": strategy,
            }
        if synthesis_input_payload is not None:
            synthesizer_event = await _consume(
                Runner(agent=self.synthesizer_agent, session_service=self.session_service, app_name="oz-startup-finder"),
                user_id="local-user",
                session_id=f"{self.session_id}:synthesizer",
                new_message=json.dumps(synthesis_input_payload, ensure_ascii=False),
                label="synthesizer",
            )
            synthesizer_json = _json_from_event_text(synthesizer_event)
            if isinstance(synthesizer_json, dict) and synthesizer_json.get("leads_json"):
                self.state.synthesis = synthesizer_json
            else:
                self.state.synthesis = self._fallback_synthesis(self.state)
        else:
            self.state.synthesis = {}

        logger.info("Pipeline complete")
        return self.state

    def _apply_db_search_state(self, *, query: str, strategy: str) -> None:
        db_path = Path(__file__).resolve().parent.parent / "data" / "startups.db"
        try:
            rows = search_companies(query, limit=20, db_path=db_path)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.debug("Direct DB search failed for query=%s: %s", query, exc)
            rows = []
        if not rows:
            logger.info("Direct DB search returned 0 rows for query=%s strategy=%s", query, strategy)
            return
        self.state.retrieved_candidates = [
            {
                "company_name": row.get("company_name"),
                "industry": row.get("industry"),
                "company_city": row.get("company_city"),
                "match_score": row.get("rank") or row.get("match_score") or 0,
                "rationale": f"DB search via {strategy}",
            }
            for row in rows
            if row.get("company_name")
        ]
        self.state.retrieval_raw_text = json.dumps(
            {"tool_used": "direct_search_companies", "query": query, "results": self.state.retrieved_candidates},
            ensure_ascii=False,
        )
        logger.info(
            "Direct DB search recovered %s candidates for query=%s strategy=%s",
            len(self.state.retrieved_candidates),
            query,
            strategy,
        )

    def _coerce_retrieval_output(self, raw: str) -> Any:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw[start: end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                pass
        return {}

    def _normalize_scorer_output(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if isinstance(data.get("leads"), list):
            items = data["leads"]
        elif isinstance(data.get("scored_leads"), list):
            items = data["scored_leads"]
        else:
            flat = {
                "company_name": data.get("company_name"),
                "relevance_score": data.get("score") or data.get("relevance_score"),
                "confidence_score": data.get("confidence_score") or data.get("score"),
                "fit_reason": data.get("feedback") or data.get("fit_reason") or "",
            }
            if any(v is not None for v in flat.values()):
                items = [flat]
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("company_name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "company_name": name,
                    "industry": item.get("industry"),
                    "company_city": item.get("company_city"),
                    "relevance_narrative": item.get("relevance_narrative") or item.get("rationale") or item.get("fit_reason") or "Matched by retrieval search.",
                    "relevance_score": item.get("relevance_score") or item.get("match_score") or item.get("score") or 60,
                    "confidence_score": item.get("confidence_score") or item.get("confidence") or item.get("score") or 60,
                }
            )
        return results

    def _fallback_synthesis(self, state: PipelineState) -> dict[str, Any]:
        raw_source = state.scored_leads or state.enriched_leads or state.retrieved_candidates
        leads_json = []
        for item in raw_source[:20]:
            leads_json.append(
                {
                    "company_name": item.get("company_name"),
                    "industry": item.get("industry"),
                    "company_city": item.get("company_city"),
                    "relevance_narrative": item.get("relevance_narrative") or item.get("rationale") or "Matched by retrieval search.",
                    "relevance_score": item.get("relevance_score") or item.get("match_score") or 60,
                    "confidence_score": item.get("confidence") or item.get("confidence_score") or 60,
                }
            )
        summary = (
            f"Found {len(leads_json)} candidate(s) for your query."
            if leads_json
            else "No leads were found in the current dataset."
        )
        return {"summary": summary, "leads_json": leads_json}
