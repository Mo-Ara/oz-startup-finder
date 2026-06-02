from __future__ import annotations

import os
import sys
import traceback

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Runtime diagnostic for the installed google-adk package.
# Prints to the Space build/run log so we can see the actual API surface.
try:
    import google.adk as _adk_root
    print("ADK_DIAG google.adk=", getattr(_adk_root, "__version__", "unknown"))
except Exception as exc:  # pragma: no cover - diagnostic only
    print("ADK_DIAG google.adk import failed:", exc)

try:
    from google.adk import Runner
    print("ADK_DIAG Runner import ok")
    print("ADK_DIAG Runner init params:", getattr(Runner.__init__, "__code__", None))
    if hasattr(Runner, "run"):
        print("ADK_DIAG Runner.run signature:", getattr(Runner.run, "__code__", None))
    if hasattr(Runner, "run_async"):
        print("ADK_DIAG Runner.run_async signature:", getattr(Runner.run_async, "__code__", None))
    append_sig = getattr(Runner, "_append_new_message_to_session", None)
    print("ADK_DIAG Runner._append_new_message_to_session:", getattr(append_sig, "__code__", append_sig))
except Exception as exc:  # pragma: no cover - diagnostic only
    print("ADK_DIAG Runner inspection failed:", exc)

try:
    from google.adk.agents import LlmAgent
    print("ADK_DIAG LlmAgent fields:", getattr(LlmAgent, "model_fields", None))
except Exception as exc:  # pragma: no cover - diagnostic only
    print("ADK_DIAG LlmAgent inspection failed:", exc)

try:
    from google.adk.runners import InvocationContext
    print("ADK_DIAG InvocationContext fields:", getattr(InvocationContext, "model_fields", None))
except Exception as exc:  # pragma: no cover - diagnostic only
    print("ADK_DIAG InvocationContext inspection failed:", exc)

try:
    from google.adk import Runner
    from google.adk.agents import LlmAgent
    from google.adk.runners import InvocationContext
    from agents.orchestrator import OzStartupFinderPipeline
    _IMPORT_OK = True
except Exception as exc:
    _IMPORT_OK = False
    print(
        "APP_STARTUP_ERROR: failed to import application code.\n",
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        flush=True,
    )
    traceback.print_exc()

import logging
import gradio as gr  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", force=True)


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
    if not confidence:
        try:
            confidence = _fmt_pct(lead.get("confidence_score"))
        except (TypeError, ValueError):
            confidence = ""

    logo_html = f"<img src='{logo}' alt='logo' class='lead-logo'/>" if logo else ""
    confidence_html = f"<span class='badge badge-conf'>{confidence}</span>" if confidence else ""
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
        <div class='lead-trace'>{confidence_html}</div>
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


def _extract_text_from_event(result) -> str:
    if result is None:
        return ""
    text = getattr(result, "text", None)
    if text:
        return str(text)
    content = getattr(result, "content", None)
    if content is None:
        content = getattr(result, "event", None)
    parts = getattr(content, "parts", None) or []
    texts = []
    for part in parts:
        value = getattr(part, "text", None)
        if value:
            texts.append(str(value))
    return "\n".join(texts).strip()


async def run_workflow(query: str):
    if not query or not query.strip():
        return "", build_leads_html([]), ""

    print(f"WORKFLOW_START query={query!r}", flush=True)
    try:
        print("PIPELINE_INIT start", flush=True)
        pipeline = OzStartupFinderPipeline()
        print("PIPELINE_INIT done", flush=True)
        state = await pipeline.run(query)
    except Exception as exc:
        tb = traceback.format_exc()
        print("WORKFLOW_ERROR:", tb, flush=True)
        return f"Workflow failed: {exc}", build_leads_html([]), tb

    trace_md = build_trace_md(state) if state else ""
    synthesis = state.synthesis if state else None
    summary = synthesis.get("summary", "") if synthesis else ""
    leads = synthesis.get("leads_json", [])[:20] if synthesis else []
    body = build_leads_html(leads)

    print(
        "UI_RETURN summary_len=",
        len(summary or ""),
        "leads=",
        len(leads or []),
        "trace_len=",
        len(trace_md or ""),
        flush=True,
    )
    print("UI_TRACE:", trace_md, flush=True)

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
.lead-link a { color: #2563eb; text-decoration: none; font-weight: 500; font-size: 13px; }
.lead-link a:hover { text-decoration: underline; }
.empty-state { color: #6b7280; font-size: 14px; padding: 18px 0; }
"""

with gr.Blocks(title="oz-startup-finder") as demo:
    gr.Markdown(
        "# oz-startup-finder\n"
        "Agentic Australian early-stage startup discovery using Google ADK, Gradio, and SQLite FTS5."
    )
    with gr.Row():
        query = gr.Textbox(
            label="",
            placeholder="Describe the startup niche you're looking for, e.g. 'AI code review tools in Melbourne'",
            scale=8,
            show_label=False,
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
    port = int(os.environ.get("GRADIO_SERVER_PORT", os.environ.get("PORT", "7860")))
    demo.launch(server_name="0.0.0.0", server_port=port, css=CSS, share=False)
