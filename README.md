---
title: oz-startup-finder
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: gradio
app_file: app.py
pinned: false
---

# oz-startup-finder

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI Build](https://img.shields.io/github/actions/workflow/status/oz-startup-finder/ci.yml?label=CI)](https://github.com/oz-startup-finder/.github/workflows/ci.yml)
[![Live Demo](https://img.shields.io/badge/Live_Demo-HuggingFace_Space-ffd43f.svg)](https://huggingface.co/spaces/Mo-Ara/oz-startup-finder)

Agentic Australian early-stage startup discovery using Google ADK, Gradio, and SQLite FTS5 — free tier end to end.

![Architecture overview](https://via.placeholder.com/1200x360/0b1220/e6edf3?text=Clarify+%E2%86%92+Router+%E2%86%92+Retrieval+%E2%86%92+Enrichment+%E2%86%92+Scoring+%E2%86%92+Synthesis)

## Demo

![Demo GIF](https://via.placeholder.com/1100x520/0b1220/e6edf3?text=30s+walkthrough+GIF+placeholder)

## Why this repo exists

This project is a portfolio example showing seven Google ADK agent patterns in a single coherent workflow:

1. Human-in-the-loop clarification
2. Routing / query classification
3. Retrieval-Augmented Generation with SQLite FTS5
4. Parallel enrichment pipeline
5. Evaluator-optimizer scoring
6. Structured output enforcement
7. Tool use on a local knowledge base

The app turns a single natural-language query like

> “AI-powered code review tools for enterprise in Melbourne”

into a ranked shortlist of matching startups with relevance narratives, confidence scores, company metadata, and exportable results.

## Agent Pipeline

```text
User Query
  │
  ▼
[1] Clarifying Agent      → narrow intent + unknowns
[2] Router Agent          → classify search strategy
[3] Retriever Agent       → FTS5 + metadata scoring
[4] Enricher Agent        → parallel relevance narratives
[5] Scorer Agent          → re-rank + confidence calibration
[6] Synthesizer Agent     → schema-safe final output
  │
  ▼
Gradio UI → cards + trace + CSV export
```

In production, enrichment runs as a safe parallel fan-out over top candidates; in tests and local demos it runs sequentially over an in-memory SQLite dataset seeded from the internal company list.

## Tech Stack

| Layer | Technology | Role |
|-------|------------|------|
| Agent framework | Google ADK (Python) | 6 agents wired in one async pipeline |
| UI | Gradio 5.x | Python-native UI; deploys to HF Spaces |
| LLM provider | OpenRouter API | Free-tier models for demo traffic |
| Retrieval | SQLite + FTS5 | Local semantic-style search over company metadata |
| Data protection | Fernet encryption | Private dataset remains unreadable in git |
| CI + deploy | GitHub Actions, Docker | Lint → test → build → deploy |
| Hosting | HuggingFace Spaces, Cloud Run | Zero-cost demo path; scalable alternative |

## Data Model

The project is a read-only client over a local SQLite database. Private source data is not stored in this repository.

Private artifacts tracked by `.env.example` and excluded via `.gitignore`:

- `data/startups.csv` — raw dataset
- `data/startups.db` — created by `scripts/build_knowledge_base.py`
- `data/startups.enc` — Fernet-encrypted database shipped to deploy targets
- `.env` — local secrets such as `OPENROUTER_API_KEY`
- `db.key` — local encryption key

```text
companies.csv
    │
    ▼  python -m scripts.build_knowledge_base companies.csv data/startups.db
startups.db  (gitignored)
    │
    ▼  encrypt with Fernet key from .env / HF Space secrets
startups.enc  (gitignored from local workflow; deployed via HF Space files)
    │
    ▼  app.py decrypts into /tmp/startups.db at runtime
SQLite queries → pipeline → UI / export
```

### Fields (example)

- `company_name`
- `company_website`
- `company_linkedin`
- `company_number_of_employees`
- `company_description`
- `industry`
- `company_city`
- `company_state`
- `company_logo_url`

Outputs never include raw descriptions. The pipeline only uses them internally for retrieval and enrichment ranking.

## Project Structure

```text
oz-startup-finder/
├── agents/
│   ├── clarifying/        # Human-in-the-loop follow-ups
│   ├── router/            # Intent classification + strategy selection
│   ├── retriever/         # SQLite FTS5 retrieval
│   ├── enricher/          # Per-lead enrichment
│   ├── scorer/            # Evaluator-optimizer scoring
│   └── synthesizer/       # Structured final output
├── shared/
│   ├── llm_factory.py     # OpenRouter client wrapper
│   ├── data_loader.py     # DB queries + connection helpers
│   ├── tools/
│   │   ├── db_search.py
│   │   ├── http_fetch.py
││   │   └── csv_export.py
│   └── prompts/           # Reusable prompt templates per agent
├── ui/
│   └── app.py             # Shared presentation helpers for Gradio
├── scripts/
│   ├── build_knowledge_base.py   # CSV → SQLite (.db not committed)
│   └── seed_demo.py              # Tiny synthetic DB for tests / quickstart
├── tests/
│   └── *.py               # Unit + contract + system smoke tests
├── .github/workflows/
│   ├── ci.yml             # Lint + test + Docker build on all PRs
│   └── deploy-hf.yml      # Push updated Space on merge to main
├── docs/
│   └── deploy.md          # HF Spaces and Cloud Run guidance
├── data/
│   └── .gitignore
├── app.py                 # Production Gradio entrypoint
├── Dockerfile
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── README.md
├── ACTION_PLAN.md
├── PRD.md
├── llms.txt
└── CONTRIBUTING.md
```

## Quick Start

### Prerequisites

- Python 3.11+
- An OpenRouter API key with free-tier model access
- Your own `companies.csv` in the project root

### 1. Create local virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Build local SQLite database

```bash
python -m scripts.build_knowledge_base companies.csv data/startups.db
```

### 3. Run the Gradio app

```bash
OPENROUTER_API_KEY=your_key python app.py
```

The app will start listening on `http://localhost:7860` by default. Set `PORT` or `GRADIO_SERVER_PORT` to override.

### 4. Run the test suite

```bash
python -m pytest tests
```

`tests/conftest.py` and `scripts/seed_demo.py` create a small synthetic SQLite database automatically. No real company data is needed to validate the agent logic or UI behavior locally.

## Deployment

### HuggingFace Spaces (recommended)

1. Create a Secret in your Space Settings named `OPENROUTER_API_KEY`.
2. If you want to deploy the private dataset, create `data/startups.enc` from `startups.db` using the repo encryption flow, upload it under `data/`, and add the Fernet key as `DB_ENCRYPTION_KEY`.
3. Connect the repo to GitHub and enable `deploy-hf.yml`, or push manually.
4. Rebuild the Space from Settings after secrets are configured.

See `docs/deploy.md` for step-by-step instructions and Cloud Run guidance.

### Docker

```bash
docker build -t oz-startup-finder .
docker run --rm -it -p 7860:7860 \
  -e OPENROUTER_API_KEY=... \
  -e DB_ENCRYPTION_KEY=... \
  -e STARTUP_DB_PATH=/data/startups.db \
  -v $(pwd)/data:/data \
  oz-startup-finder
```

## Agent Patterns Reference

Each pattern is demonstrated in a specific stage of the pipeline rather than as a standalone demo.

| Pattern | Stage | Purpose |
|--------|-------|---------|
| Human-in-the-loop | Clarifying Agent | Recommends follow-up questions such as geography, employee range, and research depth |
| Router | Router Agent | Maps user intent to a search strategy and normalization rules |
| RAG | Retriever Agent | Performs text retrieval and metadata scoring against the startup knowledge base |
| Parallel fan-out | Enricher Agent | Generates one relevance narrative per candidate concurrently |
| Sequential pipeline | Enrichment chain | Normalizes, scores, and re-ranks each candidate before final selection |
| Evaluator-optimizer | Scorer Agent | Refines top-N scoring and replaces prior stage results when thresholds are not met |
| Structured output | Synthesizer Agent | Returns a schema-constrained result with markdown summary, Card rows, and export target |

## Known Limitations

- The public repository does not include company data or decrypted databases.
- Results show logo URLs, industry, city, website, confidence, and a relevance narrative. It deliberately excludes raw descriptions and bulk CSV downloads of company metadata.
- OpenRouter free models are suitable for hobby traffic but are not guaranteed under load.
- `sqlite-vss` or external embeddings are optional in v1; FTS5-backed metadata retrieval powers v1 out of the box.

## Contributing

1. Fork the repository
2. Create a feature branch from `main`
3. Install dev dependencies and run the test suite
4. Open a Pull Request with a focused description of the change

Please see `CONTRIBUTING.md` for coding style, branch naming, commit conventions, and review expectations.

## Maintainer

Built and maintained by Mo-Ara — [GitHub](https://github.com/Mo-Ara), [LinkedIn](https://www.linkedin.com/in/mo-ara/).

## License

MIT — see `LICENSE`
