from __future__ import annotations

import os
import sys
import traceback
from typing import Any

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import gradio as gr  # noqa: E402

from agents.orchestrator import OzStartupFinderPipeline, PipelineState  # noqa: E402


def _maybe_json(obj: Any) -> str:
    try:
        import json

        return json.dumps(obj, indent=2, ensure_ascii=False) or "(empty)"
    except Exception:
        return repr(obj)


CSS = """
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
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
.step-running { animation: pulse 1.5s infinite; color: #2563eb; }
.step-done { color: #059669; }
.step-pending { color: #9ca3af; }
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
        <div class='title-group'>
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


def _step_detail(state: PipelineState | None, idx: int) -> str:
    if state is None:
        return ""
    if idx == 0:
        n = len(state.clarifying_questions or [])
        return f"<small>{n} question(s)</small>" if n else ""
    if idx == 1:
        strategy = (state.router_output or {}).get("strategy")
        return f"<small>strategy: {strategy}</small>" if strategy else ""
    if idx == 2:
        return f"<small>retrieved: {len(state.retrieved_candidates or [])}</small>"
    if idx == 3:
        return f"<small>enriched: {len(state.enriched_leads or [])}</small>"
    if idx == 4:
        return f"<small>scored: {len(state.scored_leads or [])}</small>"
    if idx == 5:
        summary = (state.synthesis or {}).get("summary")
        return f"<small>{summary}</small>" if summary else ""
    return ""


def _render_trace(state: PipelineState | None, completed_count: int) -> str:
    steps = [
        ("1. Clarify", "Identifying follow-up questions..."),
        ("2. Router", "Analyzing query intent..."),
        ("3. Retrieval", "Searching for matching startups..."),
        ("4. Enrichment", "Gathering company details..."),
        ("5. Scoring", "Ranking leads by relevance..."),
        ("6. Synthesis", "Compiling final results..."),
    ]

    lines = []
    for i in range(6):
        if i < completed_count:
            status = "✅"
            css_class = "step-done"
            detail = _step_detail(state, i)
        elif i == completed_count:
            status = "🔄"
            css_class = "step-running"
            detail = f"<small>{steps[i][1]}</small>"
        else:
            status = "⏳"
            css_class = "step-pending"
            detail = ""

        title = steps[i][0]
        if detail:
            lines.append(f"<div class='{css_class}'><b>{title}</b> {status} {detail}</div>")
        else:
            lines.append(f"<div class='{css_class}'><b>{title}</b> {status}</div>")

    return "<br>".join(lines)


def _render_results(state: PipelineState | None, done: bool = False) -> str:
    if state is None:
        return "<div class='empty-state'>Initializing...</div>"

    synthesis = state.synthesis or {}
    leads = synthesis.get("leads_json") or []

    if not leads:
        leads = (
            state.enriched_leads
            or state.scored_leads
            or state.retrieved_candidates
            or []
        )

    if leads:
        cards = "".join(_lead_card(lead) for lead in leads[:20])
        return f"<div class='leads-grid'>{cards}</div>"

    if done:
        if synthesis.get("summary"):
            return f"<div class='empty-state'>{synthesis.get('summary')}</div>"
        return "<div class='empty-state'>No leads found.</div>"

    return "<div class='empty-state'>Searching...</div>"


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
    trace = gr.HTML("")
    results_html = gr.HTML(label="Results")
    summary_md = gr.Markdown(label="Summary")
    logs = gr.HTML(value="<div class='logs'>No logs yet.</div>")

    async def run_workflow(q: str):
        if not q or not q.strip():
            logs_out = "<div class='logs'>No logs yet.</div>"
            yield "", "<div class='empty-state'>No leads yet.</div>", "", logs_out
            return

        logs_out = "<div class='logs'>Starting workflow...</div>"
        yield _render_trace(None, 0), "<div class='empty-state'>Searching...</div>", "", logs_out

        try:
            pipeline = OzStartupFinderPipeline()
        except Exception as exc:
            logs_out = f"<div class='logs'>INIT_ERROR: {exc}</div>"
            yield f"Init failed: {exc}", f"<div class='empty-state'>Init failed</div>", "", logs_out
            return

        state = None
        stage_index = 0
        try:
            async for state in pipeline.run(q):
                logs_out = f"<div class='logs'>[Stage {stage_index + 1}/6] Running...</div>"
                trace_html = _render_trace(state, stage_index)
                results_html_value = _render_results(state, done=False)
                yield trace_html, results_html_value, "", logs_out
                logs_out = f"<div class='logs'>[Stage {stage_index + 1}/6] Complete.</div>"
                stage_index += 1
        except Exception as exc:
            logs_out = f"<div class='logs'>WORKFLOW_ERROR:\\n{traceback.format_exc()}</div>"
            yield f"Workflow failed: {exc}", f"<div class='empty-state'>Workflow failed</div>", "", logs_out
            return

        trace_html = _render_trace(state or PipelineState(), min(stage_index, 6))
        summary_out = ""
        leads: list[dict] = []
        if state:
            summary_out = (state.synthesis or {}).get("summary") or ""
            leads = (
                (state.synthesis or {}).get("leads_json")
                or state.enriched_leads
                or state.scored_leads
                or state.retrieved_candidates
                or []
            )
        cards = "".join(_lead_card(lead) for lead in leads[:20])
        results_html_value = (
            f"<div class='leads-grid'>{cards}</div>" if cards else "<div class='empty-state'>No leads found.</div>"
        )
        logs_out = "<div class='logs'>Run complete.</div>"
        yield trace_html, results_html_value, summary_out, logs_out

    run.click(
        fn=run_workflow,
        inputs=query,
        outputs=[trace, results_html, summary_md, logs],
        show_progress="hidden",
    )

if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", os.environ.get("PORT", "7860")))
    demo.launch(server_name="0.0.0.0", server_port=port, css=CSS, share=False)
