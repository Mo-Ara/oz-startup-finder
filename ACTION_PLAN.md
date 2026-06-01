# oz-startup-finder — High Level Action Plan

**Living document.** Work through phases in order.
Each phase produces one PR with atomic, one-change-per-commit history.

Commit convention:
```
type: short description
Types: feat | fix | docs | ci | chore | refactor | test
```

---

## Phase 0 — Repo Scaffold
- [ ] Initialize git repo, write `.gitignore`
- [ ] Add MIT LICENSE
- [ ] Write `README.md` (outline only — expand in Phase 5)
- [ ] Write this `ACTION_PLAN.md`
- [ ] Create public GitHub repo `oz-startup-finder`
- [ ] Push initial scaffold commit

**PR:** `chore: scaffold repo, license, readme, gitignore`

---

## Phase 1 — Foundation Layer
**Goal:** Shared infra that every agent depends on, verified by tests.

1. `requirements.txt` + `pyproject.toml`
2. `shared/llm_factory.py` — OpenRouter client wrapper (config, retry, fallback)
3. `shared/data_loader.py` — SQLite connection + query helpers
4. `shared/tools/db_search.py` — FTS5 search tool for ADK agents
5. `shared/tools/http_fetch.py` — Lightweight homepage fetch (title + meta)
6. `shared/tools/csv_export.py` — Safe CSV export (metadata only, no descriptions)
7. `shared/prompts/` — Reusable prompt templates per agent role
8. `tests/conftest.py` — Fixture that builds a tiny synthetic SQLite DB from
   inline data for test runs (no real data needed)
9. `scripts/seed_demo.py` — Generates the test DB on demand
10. Verify: `python -m pytest` passes green with no agent logic yet

**PR:** `feat: foundation — llm client, data layer, shared tools, tests`

---

## Phase 2 — Agent Logic (core patterns)
**Goal:** Each agent module is independently testable.

Order of build (each module = its own commit within the phase PR):
1. `agents/router/` — Classify query type, pick search strategy
2. `agents/retriever/` — FTS5 search over SQLite DB
3. `agents/clarifying/` — Human-in-the-loop: ask follow-up questions
4. `agents/enricher/` — Per-lead enrichment (parallel-safe)
5. `agents/scorer/` — Evaluator-optimizer: relevance scoring + re-ranking
6. `agents/synthesizer/` — Format final structured output

Each module: agent code + 1–2 unit tests + prompt template in `shared/prompts/`.

**PR:** `feat: agent logic — router, retriever, clarifying, enricher, scorer, synthesizer`

---

## Phase 3 — Orchestration Layer
**Goal:** Wire all agents into one coherent workflow.

1. `agents/orchestrator.py` — Chains the 6 agents in the correct order:
   clarifying → router → retriever → enricher (parallel) → scorer → synthesizer
2. `agents/tools/` — ADK tool wrappers that ADK agents call at each step
3. `tests/test_orchestrator.py` — End-to-end test with synthetic DB
4. Verify: full pipeline runs end-to-end from a test query to structured output

**PR:** `feat: orchestrator — end-to-end agent chain with 6 patterns`

---

## Phase 4 — Gradio UI
**Goal:** One interactive app exposing the full pipeline.

1. `ui/layout.py` — Header, sidebar, trace panel, results table component
2. `ui/app.py` — Main Gradio app:
   - Query input + clarifying question flow
   - Agent trace/log sidebar (ADK events)
   - Results table (logo, name, city, industry, relevance, confidence, links)
   - Approve / Discard / Export buttons
3. Local smoke test: `python ui/app.py` works end-to-end
4. Manual deploy to HF Spaces (first deploy; CI deploy comes in Phase 6)

**PR:** `feat: gradio ui — playground with 6-agent workflow`

---

## Phase 5 — README + Polish
**Goal:** README good enough to feature on your GitHub profile.

1. One-liner + badges (CI, license, HF live demo)
2. Architecture diagram (Mermaid or inline SVG)
3. "How it works" section mapping agent patterns to app steps
4. Per-section overview: data, agents, UI, deploy
5. Live demo GIF (30s walkthrough)
6. Contributing guide (`CONTRIBUTING.md`)
7. Generate `docs/llms.txt`
8. **Fill in "Last updated" dates in PRD.md and ACTION_PLAN.md**

**PR:** `docs: readme, badges, demo gif, contributing guide, llms.txt`

---

## Phase 6 — CI/CD + Deploy Automation
**Goal:** Push to main → tests pass → Space updates automatically.

1. `.github/workflows/ci.yml`:
   - Trigger: PRs + push to main
   - Steps: checkout → setup Python → install deps → `ruff check` → `pytest` → Docker build → push to GHCR
   - Add green badge to README (already in Phase 5)
2. `.github/workflows/deploy-hf.yml`:
   - Trigger: push to main only
   - Build Docker image with `data/startups.db` preloaded
   - Push to HF Spaces via `huggingface_hub` SDK
3. Verify: merge a test branch, confirm CI runs, confirm Space updates

**PR:** `ci: github actions — lint, test, build, deploy to hf spaces`

---

## Phase 7 — Optional Enhancements (post-launch)
Only after Phases 0–6 are stable.

- [ ] Add `sqlite-vss` + embedding model for semantic search (v1 uses FTS5)
- [ ] Cloud Run deploy path with Terraform + custom domain
- [ ] Multi-language support (UI + prompts)
- [ ] Agent evaluation harness (latency, accuracy, cost per query)
- [ ] Scheduled daily refresh of knowledge base (if CSV updates regularly)
- [ ] Community contribution guide with sample dataset
- [ ] YouTube / Loom walkthrough video linked from README

---

## Important Reminders

- **Incremental commits:** one logical change per commit; no combining unrelated changes.
- **Push after every commit:** `git push` after each atomic commit.
- **PR for every phase:** do not merge directly to main.
- **No data in git:** `data/*.db` and `data/*.csv` are permanently gitignored.
- **No raw descriptions in output:** enforced by prompt + output schema; test for this.

---

*Last updated: <fill in date>*
