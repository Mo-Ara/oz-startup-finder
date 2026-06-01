from __future__ import annotations

from collections.abc import Sequence

import gradio as gr

from agents.orchestrator import OzStartupFinderPipeline, PipelineState


def build_workflow_steps(state: PipelineState) -> Sequence[str]:
    return [
        f"1. Clarify: {len(state.clarifying_questions)} question(s)",
        f"2. Router: {state.router_output.get('intent', 'pending')}",
        f"3. Retrieval: {len(state.retrieved_candidates)} candidates",
        f"4. Enrichment: {len(state.enriched_leads)} leads",
        f"5. Scoring: {len(state.scored_leads)} scored leads",
        f"6. Synthesis: {'yes' if state.synthesis else 'pending'}",
    ]


def format_results(state: PipelineState) -> str:
    if not state.synthesis:
        return "No synthesized results yet."

    summary = state.synthesis.get("summary", "")
    leads_md = ["## Summary", summary or "_Waiting for pipeline output._"]

    for lead in state.synthesis.get("leads_json", [])[:20]:
        location = ", ".join(
            filter(
                None,
                [
                    lead.get("company_city"),
                    lead.get("company_state"),
                ],
            )
        )
        leads_md.append(
            "- "
            + ", ".join(
                filter(
                    None,
                    [
                        f"**{lead.get('company_name', 'Unnamed')}**",
                        lead.get("industry"),
                        location or None,
                        f"relevance {lead.get('relevance_score')}",
                        f"confidence {lead.get('confidence_score')}",
                    ],
                )
            )
        )
        url = lead.get("company_website")
        if url:
            leads_md.append(f"  - [website]({url})")

    return "\n".join(leads_md)


async def run_workflow(query: str):
    pipeline = OzStartupFinderPipeline()
    state = await pipeline.run(query)
    trace_text = "\n".join(build_workflow_steps(state))
    results_md = format_results(state)
    csv_markdown = "No export available."
    return trace_text, results_md, csv_markdown


def export_csv(state: PipelineState) -> str:
    from shared.tools.csv_export import leads_to_csv

    leads = state.synthesis.get("leads_json", [])
    if not leads:
        return "No results to export."
    try:
        return leads_to_csv(leads)
    except Exception as exc:
        return f"Export failed: {exc}"


async def handle_export(state: PipelineState) -> tuple[str, str]:
    csv_text = export_csv(state)
    return csv_text, "CSV export ready." if csv_text and "failed" not in csv_text.lower() else csv_text
