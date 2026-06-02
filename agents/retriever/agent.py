from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from shared.adk_provider import get_model_name
from shared.data_loader import search_companies
from shared.tools.db_search import db_search

logger = logging.getLogger(__name__)


def _build_db_search_tool_output(query: str, db_path: Path) -> dict[str, Any]:
    try:
        rows = search_companies(query, limit=10, db_path=db_path)
        return {"query": query, "limit": 10, "results": rows}
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.debug("Direct db_search fallback failed for query=%s: %s", query, exc)
        return {"query": query, "limit": 0, "results": []}


def _try_extract_tool_args(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    try:
        candidates = data.get("tool_calls") or data.get("function_call") or []
        if isinstance(candidates, dict):
            candidates = [candidates]
        for item in candidates or []:
            if not isinstance(item, dict):
                continue
            function = item.get("function") if isinstance(item.get("function"), dict) else item
            arguments = function.get("arguments") if isinstance(function, dict) else None
            if isinstance(arguments, dict):
                return arguments
            if isinstance(arguments, str) and arguments.strip():
                try:
                    return json.loads(arguments)
                except Exception:
                    pass
    except Exception:
        pass
    return None


def _build_retriever_fallback(query: str, raw: str, db_path: Path) -> tuple[str, dict[str, Any]]:
    args = _try_extract_tool_args(raw)
    tool_query = (args or {}).get("query") or query
    payload = _build_db_search_tool_output(tool_query, db_path)
    response_text = json.dumps(
        {
            "tool_used": "fallback_search_companies",
            "query": payload["query"],
            "results": payload["results"],
        },
        ensure_ascii=False,
    )
    return response_text, payload


def build_retriever_agent(model: str | None = None) -> LlmAgent:
    db_path = Path(__file__).resolve().parents[2] / "data" / "startups.db"
    instruction = (
        "You are a retrieval specialist. Given a query and optional search strategy, "
        "call the db_search tool with the exact user query to return the most relevant "
        "startup candidates from the knowledge base. Maximum 10 results. "
        "Respond with JSON only, using one of these shapes:\n"
        "- { results: [ {company_name, industry, company_city, match_score, rationale} ] }\n"
        "- { top_matches: [ {company_name, industry, company_city, match_score, rationale} ] }\n"
        "Do not narrate results outside JSON.\n"
        "If you cannot or do not use the tool, still return the same JSON shape with the best matches you can."
    )

    async def _fallback_runner(ctx, invocation):
        query = invocation.user_message or ""
        text = ""
        if hasattr(invocation, "new_message"):
            parts = getattr(invocation.new_message, "parts", None) or []
            for part in parts:
                value = getattr(part, "text", None)
                if value:
                    text = value
                    break
        elif isinstance(invocation, dict):
            text = invocation.get("new_message") or invocation.get("message") or ""
        response_text, payload = _build_retriever_fallback(query or text, text, db_path)
        if hasattr(ctx, "final_response"):
            ctx.final_response(response_text)
        else:
            return response_text

    return LlmAgent(
        name="retriever",
        model=model or get_model_name(),
        instruction=instruction,
        tools=[db_search],
    )
