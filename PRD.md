# oz-startup-finder — Product Requirements Document

**Status:** Living document, updated as decisions are made  
**Owner:** Mo-Ara  
**Target repo:** `oz-startup-finder` (public GitHub)  
**Stack:** Google ADK (Python), Gradio, SQLite FTS5, GitHub Actions, HuggingFace Spaces

---

## 1. Vision

An agentic research tool that finds relevant Australian early-stage startups from an
8k-company knowledge base. One coherent workflow that showcases the full range of
ADK agent patterns — human-in-the-loop, routing, RAG, parallel enrichment, sequential
pipelines, evaluator-optimizer loops, structured output, and tool use — in a product
that is genuinely useful.

---

## 2. Goals

### Primary
- Ship a working app where a user types a niche query (e.g. "AI-powered code review
  tools for enterprise") and gets back polished lead results with relevance scoring.
- All ADK agent patterns appear in one natural workflow, not as isolated labs.
- Live demo on HuggingFace Spaces with a visible link in the README.
- Zero cost to run (OpenRouter free models, HF Spaces free tier, GitHub Actions free
  for public repos).

### Secondary
- Data separation: private company dataset lives outside version control.
- CI/CD: green badge on README, auto-deploy on merge to main.
- Docker + optional Cloud Run path for users who want their own deployment.
- `llms.txt` for AI-tool discoverability.

---

## 3. Non-Goals

- Not a generic agent tutorial or framework.
- Not production-grade for large-scale commercial use (focus is clarity and demo).
- No raw company descriptions exposed in repo, API output, or UI.
- No CSV download, no bulk export of raw data.

---

## 4. Audience

- **Primary:** GenAI / Agentic AI engineers evaluating agent design patterns.
- **Secondary:** Recruiters and hiring managers — the live demo, CI badge, and real
  dataset signal engineering maturity.
- **Tertiary:** Startup investors, analysts, or business development roles who might
  actually use the tool to discover Australian startups.

---

## 5. Data Architecture

**Private data (not in git):**
- Source: 8k-row CSV of Australian companies (local, not shared)
- Fields: company name, website, LinkedIn, employee count, description, logo URL,
  industry, city
- Build step: `scripts/build_knowledge_base.py` converts CSV → `data/startups.db`
- Deploy step: `.db` file lives in `data/` (gitignored), uploaded to HF Spaces or
  deployed with the container
- Output enforcement: raw company description is never returned by the agent or shown
  in the UI. The agent may reference it internally for matching and enrichment, but
  the response schema has no `description` field and the system prompt forbids echoing
  it.

**Public repo (code only):**
- Full UI, agent logic, prompts, CI/CD, Dockerfile
- `data/` directory tracked but empty except for `.gitignore`
- README explains: "Clone + add your own `startups.db` to run"

**Search layer:**
- SQLite with FTS5 for instant full-text search across company metadata
- Optionally pre-computed embeddings via `sqlite-vss` + a lightweight local model
  for semantic search (8k rows is small enough that FTS5 alone may suffice; leave
  room to add embeddings later without schema changes)

---

## 6. Agentic Workflow

The agent chain:

```
User query
    ↓
[1] Human-in-the-loop: clarifying questions (geography? employee range? depth?)
    ↓
[2] Router: classify query type → select search strategy
    ↓
[3] RAG / FTS5: retrieve top-k candidates from knowledge base
    ↓
[4] Parallel fan-out: enrich top-N leads concurrently (fetch metadata, generate
    relevance narrative, score confidence)
    ↓
[5] Sequential pipeline: individual enrichment steps per lead
    ↓
[6] Evaluator-optimizer: scorer evaluates output quality → re-rank / revise until
    threshold met
    ↓
[7] Structured output: markdown table + CSV download + per-company cards (logo,
    city, industry, relevance narrative, confidence, website)
```

**Pattern inventory (all present in one workflow):**

| Pattern | Role in app |
|---------|-------------|
| Human-in-the-loop | Clarifying questions; approve/discard results |
| Router | Classify query: company lookup vs. market scan vs. competitor research |
| RAG (FTS5 + optional embeddings) | Semantic search over 8k company metadata |
| Parallel fan-out | Enrich top 10 leads concurrently |
| Sequential pipeline | Per-lead enrichment chain (fetch → extract → score → format) |
| Evaluator-optimizer | Relevance scoring refinement loop |
| Structured output | JSON schema enforced, CSV export, markdown report |
| Tool use | SQLite queries, HTTP fetch, OpenRouter extraction |

---

## 7. User Interface

Gradio app with these screens:

- **Home:** App description, architecture diagram, live demo badge, "How it works."
- **Finder:** Main query input + clarifying question flow → results table with:
  - Company name, city, industry, employee range
  - Logo thumbnail
  - Relevance narrative (LLM-generated, no raw descriptions)
  - Confidence score (0–100)
  - Website link
  - Approve / Discard / Save buttons
- **Export:** Download results as CSV (metadata only, no descriptions)

**Design:** Clean, minimal — white/gray palette, company logos as thumbnails, table
with sortable columns. No dark mode required, but keep contrast high.

---

## 8. Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent framework | Google ADK (Python) | Core showcase; MIT licensed |
| UI | Gradio 5.x | Python-native, deploys to HF Spaces free |
| LLM provider | OpenRouter API (free models) | Zero API cost; Gemini Flash, Llama 3.x |
| Data store | SQLite + FTS5 (stdlib) | Zero-latency search, no external DB |
| Embeddings (opt) | sentence-transformers (local) | Optional semantic layer; 8k rows is small |
| Enrichment | `requests` + BeautifulSoup4 | Lightweight homepage fetch if needed |
| Container | Docker (slim Python base) | HF Spaces + Cloud Run compatible |
| CI | GitHub Actions | Lint, test, build, deploy |
| Docs | `llms.txt` + rich README | AI-tool discovery |

---

## 9. Cost Analysis

| Item | Cost | Notes |
|------|------|-------|
| OpenRouter free models | $0 | Soft rate limits; fine for hobby/demo traffic |
| HF Spaces (CPU small) | $0 | Free tier, suitable for this workload |
| GitHub Actions (public repo) | $0 | 2,000 min/month free |
| SQLite / FTS5 | $0 | Bundled with Python |
| Docker / Gradio | $0 | Open source |
| **Total** | **$0/month** | |

Optional (not required):
- Cloud Run: $0–5/month for hobby traffic; enables custom domain
- Custom domain: ~$10–15/year
- HF Pro: $9/month (GPU/custom domain, not needed)

---

## 10. Repository Structure

```
oz-startup-finder/
├── agents/
│   ├── clarifying/
│   │   └── agent.py                 # Human-in-the-loop: asks follow-up Qs
│   ├── router/
│   │   └── agent.py                 # Classifies query, picks strategy
│   ├── retriever/
│   │   └── agent.py                 # FTS5/embedding search over DB
│   ├── enricher/
│   │   └── agent.py                 # Per-lead enrichment (parallel-safe)
│   ├── scorer/
│   │   └── agent.py                 # Evaluator-optimizer: refine scores
│   └── synthesizer/
│       └── agent.py                 # Format final output
├── shared/
│   ├── llm_factory.py               # OpenRouter client, retry, fallback
│   ├── data_loader.py               # SQLite connection + query helpers
│   ├── tools/
│   │   ├── db_search.py             # FTS5 search tool for ADK
│   │   ├── http_fetch.py            # Lightweight homepage fetch
│   │   └── csv_export.py            # Safe export (no descriptions)
│   └── prompts/                     # Reusable prompt templates
├── ui/
│   ├── app.py                       # Gradio entrypoint
│   └── layout.py                    # Shared components
├── scripts/
│   ├── build_knowledge_base.py      # CSV → SQLite (.db never committed)
│   └── seed_demo.py                 # Optionally generates synthetic DB for forks
├── data/
│   ├── .gitignore                   # Ignores *.db, *.csv
│   └── startups.db                  # GENERATED, not in git
├── tests/
│   ├── conftest.py                  # Shared fixtures + synthetic DB seed
│   ├── test_router.py
│   ├── test_retriever.py
│   └── test_evaluator.py
├── .github/
│   └── workflows/
│       ├── ci.yml                   # Lint + test on PR
│       └── deploy-hf.yml            # Sync to HF Spaces on merge to main
├── deploy/
│   ├── Dockerfile
│   └── cloudbuild.yaml              # Optional Cloud Run path
├── docs/
│   └── llms.txt                     # AI-tool-optimized reference
├── PRD.md                           # This product doc (can move to docs/)
├── ACTION_PLAN.md                   # Living phase tracker
├── README.md
├── CONTRIBUTING.md
├── LICENSE                          # MIT
├── requirements.txt
└── pyproject.toml
```

---

## 11. CI/CD Pipeline

**`.github/workflows/ci.yml`** (on PR + push to main):
1. Checkout code
2. Setup Python + install deps from `requirements.txt`
3. Lint: `ruff check`
4. Test: `pytest` (uses `scripts/seed_demo.py` to create a tiny synthetic DB for tests)
5. Build: Docker image → GitHub Container Registry
6. **Status badge** on README

**`.github/workflows/deploy-hf.yml`** (on merge to main only):
1. Build Docker image with `data/startups.db` preloaded (stored as HF Space secret or
   mounted from a private HF Dataset — whichever is simpler to set up)
2. Push to HF Spaces via `huggingface_hub` Python SDK
3. Space auto-builds from the pushed image

---

## 12. Data Security & Privacy Rules

These rules are enforced in code and prompts; they also belong in the README.

- **No raw company descriptions in the repo.** The `data/` directory is gitignored.
- **No raw descriptions in agent output.** The system prompt forbids quoting or
  paraphrasing descriptions. The output schema has no `description` field.
- **No CSV download.** No API endpoint or UI button serves the raw CSV or the
  SQLite `.db` file.
- **Forks get code only.** Contributors can run the app with their own dataset by
  pointing `DATA_PATH` to their own SQLite file.

---

## 13. Success Criteria

- [ ] All 8 agent patterns wired into one coherent workflow
- [ ] Gradio UI live on HF Spaces with working demo link in README
- [ ] CI badge green on README
- [ ] Agent never outputs raw company descriptions (verified by prompt + schema)
- [ ] `llms.txt` discoverable by AI coding tools
- [ ] README has architecture diagram, 30s demo GIF, deploy instructions
- [ ] SQLite search returns candidates in <500ms for any query over 8k rows
- [ ] All code reviewed via PR; no direct pushes to main

---

## 14. Decision Log

| Date | Decision | Context |
|------|----------|---------|
| TBD | FTS5-only vs FTS5 + sqlite-vss embeddings | FTS5 likely sufficient for 8k rows; defer embeddings unless recall suffers |
| TBD | HF Space secrets vs private HF Dataset for .db file | Secrets are simpler for a single file; Dataset is cleaner for versioning |
| TBD | Whether to add Cloud Run deploy path in v1 or defer to post-launch | Defer unless user explicitly wants GCP custom domain |
| TBD | OpenRouter fallback model if free tier rate-limits | Add secondary free model (e.g. Gemini Flash Lite) |

---

*Last updated: <fill in date>*
