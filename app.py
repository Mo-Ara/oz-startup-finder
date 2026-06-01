from __future__ import annotations

import os
import sys

# Ensure repo root is importable for package-style 'agents' / 'shared' imports
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import gradio as gr  # noqa: E402
from agents.orchestrator import OzStartupFinderPipeline  # noqa: E402
from shared.tools.csv_export import leads_to_csv  # noqa: E402


def _location(lead: dict) -> str:
    city = (lead or {}).get("company_city") or ""
    state = (lead or {}).get("company_state") or ""
    parts = [part for part in [city, state] if part]
    return ", ".join(parts)


def _fmt_pct(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def format_results(synthesis: dict) -> str:
    if not synthesis:
        return "No synthesized results yet."

    summary = synthesis.get("summary", "")
    leads = synthesis.get("leads_json", [])[:20]
    lines = ["## Summary", summary or "_Waiting for pipeline output._"]
    for lead in leads:
        name = lead.get("company_name") or "Unnamed"
        industry = lead.get("industry") or ""
        location = _location(lead)
        confidence = _fmt_pct(lead.get("confidence_score"))
        relevance = _fmt_pct(lead.get("relevance_score"))
        extras = [industry, location, f"relevance {relevance}", f"confidence {confidence}"]
        extras = [item for item in extras if item]
        lines.append(f"- **{name}**" + ((" — " + ", ".join(extras)) if extras else ""))
        url = lead.get("company_website")
        if url:
            lines.append(f"  - [website]({url})")
    return "\n".join(lines)


async def run_workflow(query: str):
    if not query or not query.strip():
        return "Enter a niche to start.", "No results yet.", ""

    pipeline = OzStartupFinderPipeline()
    state = await pipeline.run(query)

    if not state or state.synthesis is None:
        return "Workflow finished with no output.", "No results.", ""

    trace_parts = [
        f"1. Clarify: {len(state.clarifying_questions or [])} question(s)",
        f"2. Router: {(state.router_output or {}).get('intent', 'pending')}",
        f"3. Retrieval: {len(state.retrieved_candidates or [])} candidates",
        f"4. Enrichment: {len(state.enriched_leads or [])} leads",
        f"5. Scoring: {len(state.scored_leads or [])} scored leads",
        f'6. Synthesis: {"yes" if state.synthesis else "pending"}',
    ]
    trace_md = "\n".join(trace_parts)
    results_md = format_results(state.synthesis)

    csv_text = ""
    try:
        leads = state.synthesis.get("leads_json", [])
        if leads:
            csv_text = leads_to_csv(leads)
    except Exception as exc:  # pragma: no cover
        csv_text = f"Export failed: {exc}"

    return trace_md, results_md, csv_text


with gr.Blocks(title="oz-startup-finder") as demo:
    gr.Markdown(
        "# oz-startup-finder\n"
        "Agentic Australian early-stage startup discovery using Google ADK, Gradio, and SQLite FTS5."
    )
    query = gr.Textbox(label="Describe the startup niche you're looking for", placeholder="e.g. AI-powered code review tools for enterprise")
    run = gr.Button("Run workflow", variant="primary")
    with gr.Row():
        trace = gr.Markdown(label="Workflow trace")
        results = gr.Markdown(label="Results")
    csv_output = gr.Textbox(label="CSV output", lines=12)
    run.click(fn=run_workflow, inputs=query, outputs=[trace, results, csv_output])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    demo.launch(server_name="0.0.0.0", server_port=port)
