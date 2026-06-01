from __future__ import annotations

from typing import Sequence

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


async def run_workflow(query: str) -> tuple[str, str]:
    pipeline = OzStartupFinderPipeline()
    state = await pipeline.run(query)
    steps = build_workflow_steps(state)
    step_text = "\n".join(steps)
    summary = state.synthesis.get("summary", "")
    return step_text, summary


with gr.Blocks(title="oz-startup-finder") as app:
    trace = gr.Textbox(label="Agent workflow", lines=6)
    chat = gr.Textbox(label="Research request", placeholder="AI-powered code review...")
    response = gr.Markdown(label="Results")
    chat.submit(run_workflow, [chat], [trace, response])


if __name__ == "__main__":
    app.launch()
