from __future__ import annotations

from google.adk.agents import LlmAgent

from shared.llm_factory import get_llm
from shared.prompts.synthesizer import SYNTHESIZER_SYSTEM_PROMPT


def build_synthesizer_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name="synthesizer",
        model=model or get_llm(),
        instruction=SYNTHESIZER_SYSTEM_PROMPT,
        description=(
            "Final output formatter. Accepts scored leads and produces a clean, human-readable "
            "summary and a JSON array of lead objects in the exact schema required by the UI. "
            "Never includes raw company descriptions. "
            "Output: { summary: str, leads_json: [{company_name, industry, company_city, relevance_score, confidence_score, company_website, company_linkedin}] }"
        ),
    )
