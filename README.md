# oz-startup-finder

Agentic research tool that finds relevant Australian early-stage startups from an 8k-company knowledge base, using semantic search, parallel enrichment, and relevance scoring — built with Google ADK.

Built to showcase the full range of ADK agent patterns in one coherent workflow. Designed to be free to run and easy to deploy.

> **Live demo:** _(coming soon — HuggingFace Spaces)_

---

## How it works

```
User query + clarifying questions
  → Router (classify intent)
  → RAG / FTS5 search over 8k companies
  → Parallel enrichment of top candidates
  → Evaluator-optimizer scoring loop
  → Structured output: table + CSV export + per-company cards
```

Eight ADK patterns in one pipeline:

| Pattern | Where |
|---------|-------|
| Human-in-the-loop | Clarifying questions; approve / discard results |
| Router | Classify query: company lookup vs. market scan vs. competitor research |
| RAG (FTS5 + optional embeddings) | Semantic search over 8k company metadata |
| Parallel fan-out | Enrich top 10 leads concurrently |
| Sequential pipeline | Per-lead enrichment chain: fetch → extract → score → format |
| Evaluator-optimizer | Relevance scoring refinement loop |
| Structured output | JSON schema enforced, CSV export, markdown report |
| Tool use | SQLite queries, HTTP fetch, OpenRouter extraction |

---

## Tech stack

| Layer | Tool |
|-------|------|
| Agent framework | Google ADK (Python) |
| UI | Gradio |
| LLM | OpenRouter (free models) |
| Data | SQLite + FTS5 |
| Container | Docker |
| CI / Deploy | GitHub Actions → HuggingFace Spaces |

**Cost: $0/month** (free tiers across the board).

---

## Local development

### 1. Clone

```bash
git clone https://github.com/<your-username>/oz-startup-finder.git
cd oz-startup-finder
```

### 2. Set up environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Build the knowledge base

```bash
python scripts/build_knowledge_base.py /path/to/your/companies.csv
```

This creates `data/startups.db` (gitignored, never committed).

### 4. Run the app

```bash
python ui/app.py
```

---

## Data privacy

This repo contains **application code only** — no raw company data.

- `data/startups.db` is gitignored and must be built locally from your CSV.
- The agent is explicitly instructed never to echo raw company descriptions.
- The output schema has no `description` field.
- No CSV download or bulk-export of raw data is available in the UI.

Forks and clones get the full app but zero access to the private knowledge base.

---

## Project docs

- `PRD.md` — product requirements, architecture, cost analysis, decision log
- `ACTION_PLAN.md` — phase-by-phase build tracker

---

## License

MIT — see `LICENSE`

---

## Status

🚧 Under active construction — Phases 0–1 in progress.
