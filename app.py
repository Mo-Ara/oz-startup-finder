from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import gradio as gr  # noqa: E402
from agents.orchestrator import OzStartupFinderPipeline  # noqa: E402


def _location(lead: dict) -> str:
    city = (lead or {}).get("company_city") or ""
    state = (lead or {}).get("company_state") or ""
    parts = [part for part in [city, state] if part]
    return ", ".join(parts)


def _fmt_pct(value) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return ""


def lead_card(lead: dict) -> str:
    name = lead.get("company_name") or "Unnamed"
    industry = lead.get("industry") or ""
    location = _location(lead)
    website = lead.get("company_website") or ""
    logo = lead.get("company_logo_url") or ""
    confidence = _fmt_pct(lead.get("confidence"))
    relevance = ""
    if not confidence:
        try:
            raw_conf = lead.get("confidence_score")
            if raw_conf is not None:
                confidence = _fmt_pct(raw_conf)
        except (TypeError, ValueError):
            confidence = ""

    logo_html = f"<img src='{logo}' alt='logo' class='lead-logo'/>" if logo else ""
    confidence_html = f"<span class='badge badge-conf'>{confidence}</span>" if confidence else ""
    relevance_html = f"<span class='badge badge-rel'>{relevance}</span>" if relevance else ""
    location_html = f"<span class='meta'>{location}</span>" if location else ""
    industry_html = f"<span class='meta'>{industry}</span>" if industry else ""
    website_html = f"<a href='{website}' target='_blank'>website</a>" if website else ""

    return f"""
    <div class='lead-card'>
      <div class='lead-header'>
        <div class='lead-title-group'>
          <div class='lead-name'>{name}</div>
          <div class='lead-meta-row'>{industry_html} {location_html}</div>
        </div>
        {logo_html}
      </div>
      <div class='lead-body'>
        <div class='lead-trace'>{relevance_html} {confidence_html}</div>
        <div class='lead-link'>{website_html}</div>
      </div>
    </div>
    """


def build_leads_html(leads: list[dict]) -> str:
    if not leads:
        return "<div class='empty-state'>No leads yet. Try a niche like 'fintech Melbourne'.</div>"
    cards = "".join(lead_card(lead) for lead in leads)
    return f"<div class='leads-grid'>{cards}</div>"


def build_trace_md(state) -> str:
    if state is None:
        return ""
    items = [
        f"1. Clarify: {len(state.clarifying_questions or [])} question(s)",
        f"2. Router: {(state.router_output or {}).get('strategy', 'pending')}",
        f"3. Retrieval: {len(state.retrieved_candidates or [])} candidates",
        f"4. Enrichment: {len(state.enriched_leads or [])} leads",
        f"5. Scoring: {len(state.scored_leads or [])} scored leads",
        f"6. Synthesis: {'yes' if state.synthesis else 'pending'}",
    ]
    return "\n".join(items)


async def run_workflow(query: str):
    if not query or not query.strip():
        return "", build_leads_html([]), ""

    pipeline = OzStartupFinderPipeline()
    state = await pipeline.run(query)

    trace_md = build_trace_md(state) if state else ""
    synthesis = state.synthesis if state else None
    summary = synthesis.get("summary", "") if synthesis else ""
    leads = synthesis.get("leads_json", [])[:20] if synthesis else []
    body = build_leads_html(leads)

    return summary, body, trace_md


CSS = """
.leads-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-top: 10px; }
.lead-card { border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px; background: #ffffff; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.lead-header { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.lead-title-group { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.lead-name { font-size: 17px; font-weight: 700; color: #111827; line-height: 1.2; word-break: break-word; }
.lead-meta-row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; color: #4b5563; font-size: 13px; }
.lead-logo { width: 48px; height: 48px; border-radius: 10px; object-fit: cover; border: 1px solid #e5e7eb; background: #f9fafb; }
.lead-body { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.meta { background: #f3f4f6; color: #374151; padding: 3px 8px; border-radius: 999px; font-size: 12px; font-weight: 500; }
.badge { padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-conf { background: #eef2ff; color: #1d4ed8; }
.badge-rel { background: #f5f3ff; color: #7c3aed; }
.lead-link a { color: #2563eb; text-decoration: none; font-weight: 500; font-size: 13px; }
.lead-link a:hover { text-decoration: underline; }
.empty-state { color: #6b7280; font-size: 14px; padding: 18px 0; }
"""

with gr.Blocks(title="oz-startup-finder", css=CSS) as demo:
    gr.Markdown(
        "# oz-startup-finder\n"
        "Agentic Australian early-stage startup discovery using Google ADK, Gradio, and SQLite FTS5."
    )
    with gr.Row():
        query = gr.Textbox(
            label="",
            placeholder="Describe the startup niche you're looking for, e.g. 'AI code review tools in Melbourne'",
            scale=8,
        )
        run = gr.Button("Run workflow", variant="primary", scale=2)

    with gr.Row():
        with gr.Column(scale=2):
            results_html = gr.HTML(label="Results")
        with gr.Column(scale=1):
            with gr.Accordion("Trace", open=False):
                trace_md = gr.Markdown()
            summary_md = gr.Markdown(label="Summary")

    run.click(fn=run_workflow, inputs=query, outputs=[summary_md, results_html, trace_md])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    demo.launch(server_name="0.0.0.0", server_port=port)
