from __future__ import annotations

from google.adk.agents import LlmAgent

from shared.llm_factory import get_model_name
from shared.prompts.scorer import SCORER_SYSTEM_PROMPT


def build_scorer_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name="scorer",
        model=model or get_model_name(),
        instruction=SCORER_SYSTEM_PROMPT,
        description=(
            "Evaluator-optimizer agent. Accepts enriched leads and assigns a relevance_score "
            "and confidence_score. Re-ranks by aggregate fit. "
            "Output JSON: { scored_leads: [{company_name, relevance_score, confidence_score, fit_reason}] }"
        ),
    )
