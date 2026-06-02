from __future__ import annotations

from google.adk.agents import LlmAgent

from shared.adk_provider import get_model_name
from shared.prompts.clarifying import CLARIFYING_SYSTEM_PROMPT


def build_clarifying_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name="clarifying",
        model=model or get_model_name(),
        instruction=CLARIFYING_SYSTEM_PROMPT,
        description=(
            "Human-in-the-loop agent. Asks short follow-up questions when the user request "
            "is ambiguous, missing constraints, or would benefit from narrowing. "
            "Outputs JSON: { follow_up_questions: [str] or [], ready: bool }"
        ),
    )
