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
    summary = ""
    markdown_parts = []
    leads = state.synthesis.get("leads_json", []) if state.synthesis else []

    if not leads:
        fallback = (
            state.scored_leads
            or state.enriched_leads
            or state.retrieved_candidates
        )
        summary = (
            state.synthesis.get("summary", "")
            if state.synthesis
            else "No synthesized results yet."
        )
        if fallback:
            markdown_parts.append("## Summary")
            markdown_parts.append(summary or "_Waiting for pipeline output._")
            markdown_parts.append(
                f"_Showing {len(fallback)} fallback candidate(s) because synthesis did not return leads._"
            )
            for lead in fallback[:20]:
                location = ", ".join(
                    filter(
                        None,
                        [
                            lead.get("company_city"),
                            lead.get("company_state"),
                        ],
                    )
                )
                markdown_parts.append(
                    "- "
                    + ", ".join(
                        filter(
                            None,
                            [
                                f"**{lead.get('company_name', 'Unnamed')}**",
                                lead.get("industry"),
                                location or None,
                            ],
                        )
                    )
                )
            return "\n".join(markdown_parts)

        markdown_parts.append("## Summary")
        markdown_parts.append(summary or "_No leads were found in the current dataset._")
        return "\n".join(markdown_parts)

    summary = state.synthesis.get("summary", "")
    leads_md = ["## Summary", summary or "_Waiting for pipeline output._"]

    for lead in leads[:20]:
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
    async for state in pipeline.run(query):
        trace_text = "\n".join(build_workflow_steps(state))
        results_md = format_results(state)
        yield trace_text, results_md


def export_csv(state: PipelineState) -> str:
    from shared.tools.csv_export import leads_to_csv

    leads = state.synthesis.get("leads_json", []) if state.synthesis else []
    if not leads:
        return "No results to export."
    try:
        return leads_to_csv(leads)
    except Exception as exc:
        return f"Export failed: {exc}"


async def handle_export(state: PipelineState) -> tuple[str, str]:
    csv_text = export_csv(state)
    return csv_text, "CSV export ready." if csv_text and "failed" not in csv_text.lower() else csv_text
