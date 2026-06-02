from __future__ import annotations

import os
import sys
import traceback
from typing import Any

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import gradio as gr  # noqa: E402

from agents.orchestrator import OzStartupFinderPipeline  # noqa: E402


def _maybe_json(obj: Any) -> str:
    try:
        import json

        return json.dumps(obj, indent=2, ensure_ascii=False) or "(empty)"
    except Exception:
        return repr(obj)


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
.lead-link a { color: #2563eb; text-decoration: none; font-weight: 500; font-size: 13px; }
.lead-link a:hover { text-decoration: underline; }
.empty-state { color: #6b7280; font-size: 14px; padding: 18px 0; }
.logs { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; white-space: pre-wrap; background:#0b1220; color:#e6edf3; padding:14px; border-radius:12px; max-height:280px; overflow:auto; }
"""


def _lead_card(lead: dict) -> str:
    name = lead.get("company_name") or "Unnamed"
    industry = lead.get("industry") or ""
    location = lead.get("company_city") or ""
    website = lead.get("company_website") or ""
    logo = lead.get("company_logo_url") or ""
    confidence = lead.get("confidence") or lead.get("confidence_score") or ""
    try:
        confidence = f"{float(confidence):.1f}%"
    except (TypeError, ValueError):
        confidence = ""

    logo_html = f'<img src="{logo}" alt="logo" class="lead-logo"/>' if logo else ""
    confidence_html = f'<span class="badge badge-conf">{confidence}</span>' if confidence else ""
    location_html = f'<span class="meta">{location}</span>' if location else ""
    industry_html = f'<span class="meta">{industry}</span>' if industry else ""
    website_html = f'<a href="{website}" target="_blank">website</a>' if website else ""

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
        <div class='lead-trace'>{confidence_html}</div>
        <div class='lead-link'>{website_html}</div>
      </div>
    </div>
    """


with gr.Blocks(title="oz-startup-finder") as demo:
    gr.Markdown(
        "# oz-startup-finder\n"
        "Agentic Australian early-stage startup discovery using Google ADK, Gradio, and SQLite FTS5."
    )
    query = gr.Textbox(
        label="",
        placeholder="Describe the startup niche you're looking for, e.g. 'AI code review tools in Melbourne'",
        scale=8,
        show_label=False,
    )
    run = gr.Button("Run workflow", variant="primary", scale=2)
    trace = gr.Markdown("")
    results_html = gr.HTML(label="Results")
    summary_md = gr.Markdown(label="Summary")
    logs = gr.HTML(value="<div class='logs'>No logs yet.</div>")

    async def run_workflow(q: str):
        if not q or not q.strip():
            logs_out = "<div class='logs'>No logs yet.</div>"
            yield "", "<div class='empty-state'>No leads yet.</div>", "", logs_out
            return

        logs_out = "<div class='logs'>Starting workflow...</div>"
        yield "Running: clarifying...", "<div class='empty-state'>Processing...</div>", "", logs_out

        try:
            pipeline = OzStartupFinderPipeline()
        except Exception as exc:
            logs_out = f"<div class='logs'>INIT_ERROR: {exc}</div>"
            yield f"Init failed: {exc}", "<div class='empty-state'>Init failed</div>", "", logs_out
            return

        state = None
        try:
            state = await pipeline.run(q)
        except Exception as exc:
            logs_out = f"<div class='logs'>WORKFLOW_ERROR:\n{traceback.format_exc()}</div>"
            yield f"Workflow failed: {exc}", "<div class='empty-state'>Workflow failed</div>", "", logs_out
            return

        trace_out = ""
        results_out = "<div class='empty-state'>No leads found.</div>"
        summary_out = ""
        logs_out = "<div class='logs'>Run complete.</div>"

        if state is not None:
            router_output = state.router_output or {}
            trace_out = "\n".join([
                f"### 2. Router\n```\n{_maybe_json(router_output)}\n```",
                f"### 3. Retrieval\n```\nretrieved: {len(state.retrieved_candidates or [])}\n```",
                f"### 4. Enrichment\n```\nenriched: {len(state.enriched_leads or [])}\n```",
                f"### 5. Scoring\n```\nscored: {len(state.scored_leads or [])}\n```",
                f"### 6. Synthesis\n```\n{_maybe_json(state.synthesis or {})}\n```",
            ])
            synthesis = state.synthesis or {}
            summary_out = synthesis.get("summary") or ""
            leads = synthesis.get("leads_json") or []
            if not leads:
                leads = state.enriched_leads or state.scored_leads or []
            cards = "".join(_lead_card(lead) for lead in leads[:20])
            results_out = f"<div class='leads-grid'>{cards}</div>" if cards else "<div class='empty-state'>No leads found.</div>"

        yield trace_out, results_out, summary_out, logs_out

    run.click(
        fn=run_workflow,
        inputs=query,
        outputs=[trace, results_html, summary_md, logs],
        show_progress="hidden",
    )

if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", os.environ.get("PORT", "7860")))
    demo.launch(server_name="0.0.0.0", server_port=port, css=CSS, share=False)
