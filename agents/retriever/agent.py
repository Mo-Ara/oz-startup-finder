from google.adk.agents import LlmAgent

from shared.adk_provider import get_model_name
from shared.tools.db_search import db_search


def build_retriever_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name="retriever",
        model=model or get_model_name(),
        instruction=(
            "You are a retrieval specialist. Given a query and optional search strategy, "
            "use the db_search tool to return the most relevant startup candidates from the "
            "knowledge base. Always justify selections with evidence from company_name, "
            "industry, company_city, and any other allowed fields. Maximum of 10 results.\n\n"
            "Output JSON: { top_matches: [{company_name, industry, company_city, match_score, rationale}] }"
        ),
        tools=[db_search],
    )
