from __future__ import annotations

from google.adk.agents import LlmAgent

from shared.llm_factory import get_llm
from shared.prompts.enricher import ENRICHER_SYSTEM_PROMPT


def build_enricher_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name="enricher",
        model=model or get_llm(),
        instruction=ENRICHER_SYSTEM_PROMPT,
        description=(
            "Per-lead enrichment agent. Generates concise relevance narratives for a batch "
            "of candidate startups. May run in parallel for multiple leads. "
            "Output JSON per lead: { relevance_narrative, inferred_stage, inferred_value_prop }"
        ),
    )
