# oz-startup-finder

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An agentic research tool that finds relevant Australian early-stage startups from an 8k-company knowledge base. Built with Google ADK, Gradio, and SQLite FTS5.

## Why this repo exists

This project showcases a full agentic pipeline in one workflow:
human-in-the-loop clarification, routing, retrieval, parallel enrichment, evaluator-optimizer scoring, and structured output.

## Architecture

```text
User Query
  |
  v
[1] Clarifying Agent      -> narrow the intent
[2] Router Agent          -> classify + choose search strategy
[3] Retriever Agent       -> SQLite FTS5 candidate search
[4] Enricher Agent        -> parallel relevance narratives
[5] Scorer Agent          -> relevance + confidence scoring
[6] Synthesizer Agent     -> final structured output
  |
  v
Gradio UI -> table + cards + CSV export
```

## Tech Stack

- Google ADK (Python)
- Gradio 5.x
- SQLite + FTS5
- OpenRouter free models
- GitHub Actions
- Docker

## Data

Private company data is **not** in this repo.
Build `data/startups.db` locally with `scripts/seed_demo.py` or `scripts/build_knowledge_base.py`.
`data/*.db` and `data/*.csv` are gitignored.

## Quick Start

```bash
python -m scripts.seed_demo
python ui/app.py
```

## Live Demo

Coming soon.
