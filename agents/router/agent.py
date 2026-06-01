from __future__ import annotations

from google.adk.agents import LlmAgent

from shared.llm_factory import get_llm
from shared.prompts.router import ROUTER_SYSTEM_PROMPT


def build_router_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name="router",
        model=model or get_llm(),
        instruction=ROUTER_SYSTEM_PROMPT,
        description=(
            "Classifies the user query into an intent type and picks a search strategy. "
            "Outputs JSON with fields 'intent' and 'strategy'."
        ),
    )
