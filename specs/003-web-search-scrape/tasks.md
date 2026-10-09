---
description: "Task list for feature implementation"
---

# Tasks: Grouped Web Research — Multi-Engine Search with Outline-Preserving Page Scraping

**Input**: Design documents from `specs/003-web-search-scrape/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/web-research-tool.md, quickstart.md

**Tests**: INCLUDED and binding — the user's plan note ("create test cases and add error handling") + Constitution II. Every task references its row(s) in the research.md D6 error-handling matrix; RED tests precede their implementations. No live web in CI: search mocked at the provider interface, pages served by local fixtures.

**Organization**: Tasks grouped by user story; each story independently testable (US1 = search surface, US2 = grouped extraction + evidence upgrade, US3 = rendering).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project: `src/`, `tests/` at repository root (package `agentic_rag_mcp`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies, config surface, and the deterministic test fixtures every later phase builds on

- [X] T001 Add `beautifulsoup4` and `lxml` to `dependencies` in pyproject.toml (the only new deps — research.md D2), install into the venv, and verify with `python -c "import bs4, lxml"`; confirm litellm is NOT added (spec Clarifications)
- [X] T002 [P] Add `[web.research]` to src/agentic_rag_mcp/config.py + DEFAULT_CONFIG per research.md D8, quoting constraints verbatim: `max_pages = 3` (cap 5), `per_page_chars = 6000`, `fetch_timeout_s = 15.0`, `overall_timeout_s = 30.0` (FR-014), `max_concurrent = 4`
- [X] T003 [P] Create deterministic scrape fixtures: tests/fixtures/research/ordered.html (h2 → p → img → p document order), js_only.html (no extractable content), oversized.html (> per_page_chars), dirty.html (data: URI images + relative srcs + short paragraphs), and a local HTTP fixture-server helper in tests/integration/conftest.py with endpoints: /slow (delay > fetch timeout), /forbidden (403), /normal (serves ordered.html)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two shared mechanisms every story needs — chain provenance/dedup and the SSRF guard

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Write failing unit tests tests/unit/test_research_chain.py for the extended chain (research.md D6 rows 1, 2, 10): one engine raising → next serves and every hit carries its `engine` field; two engines returning the same URL → deduped keeping first ranking; all engines down → honest empty result with error state, never fabricated hits (FR-001/003/004)
- [X] T005 Make T004 pass: extend src/agentic_rag_mcp/search/web/base.py — per-hit `engine` provenance, URL dedup keeping first ranking; the frozen fields `title, url, snippet` stay byte-identical (FR-002 / SC-001 — existing tests/contract/test_web_providers.py must stay green untouched)
- [X] T006 Write failing unit tests tests/unit/test_research_guard.py (research.md D6 row 6): private address refused, loopback refused, link-local refused, public allowed, and a public URL redirecting to a private address refused (resolver mocked — no network)
- [X] T007 Make T006 pass: implement the guarded fetch in src/agentic_rag_mcp/search/web/research.py — resolve hostname, refuse if ANY address is `is_private | is_loopback | is_link_local | is_unspecified` (ipaddress stdlib), follow redirects hop-by-hop (≤3) re-checking each hop (FR-013; research.md D4)

**Checkpoint**: Foundation ready — provenance-carrying chain + guarded fetch, all tests green

---

## Phase 3: User Story 1 — Multi-Engine Search Surface (Priority: P1) 🎯 MVP

**Goal**: `web_research(query, limit)` exists and returns ranked hits with engine provenance, dedup, and honest error states — the search half of the tool, before scraping

**Independent Test**: Call the tool with the chain mocked (one engine down): hits return with `title, url, snippet` + `engine`, `engines_used` aggregates, `elapsed_ms` present, and an all-down call returns `hits: []` with a non-null error (quickstart.md S1 search fields; contract invariants 1, 7, 8)

### Tests for User Story 1

- [X] T008 [P] [US1] Write failing contract tests tests/contract/test_web_research_contract.py pinning the response schema v1 (contracts/web-research-tool.md): per-hit frozen fields + `engine`; top-level `query, engines_used, elapsed_ms, error`; limit capped at config `max_pages = 3` (cap 5); all-engines-down → `hits: []` + non-null `error` (research.md D6 rows 10, 13)

### Implementation for User Story 1

- [X] T009 [US1] Implement `web_research(query, limit=3)` v1 in src/agentic_rag_mcp/server.py: search via the extended chain only (no scraping yet), assemble the ResearchResult v1 per data-model.md, and confirm `web_search` responses remain byte-identical (FR-011 search half; FR-002)

**Checkpoint**: MVP — grouped research's search surface is live and contract-tested; scraping/US2 can proceed independently

---

## Phase 4: User Story 2 — Grouped Extraction, Bounds, Fallbacks, Evidence Upgrade (Priority: P1)

**Goal**: Each hit gets scrape → sections (document order, text+image grouped) → bounded content, with honest fallbacks everywhere; the ask pipeline's live-web evidence upgrades to the same grouped content

**Independent Test**: Fixture-server integration (chain mocked): /normal yields sections with blocks in h2→p→img→p order; /slow and /forbidden fall back to snippet with `status_reason`; oversized.html truncates with `truncated: true`; ask live_web evidence carries grouped `content` (quickstart.md S2, S5)

### Tests for User Story 2 (all RED before the implementations)

- [X] T010 [P] [US2] Write failing unit tests tests/unit/test_research_extraction.py against the fixtures (research.md D6 rows 5, 7, 8, 9): ordered.html → sections preserve document order with text+image grouped (SC-003 ≥90% basis); js_only.html → empty sections tolerated, no crash; oversized.html → truncated at `per_page_chars = 6000` and flagged; dirty.html → `data:` URIs skipped, relative srcs absolutized, <30-char paragraphs dropped
- [X] T011 [P] [US2] Write failing integration tests tests/integration/test_web_research.py (fixture server; chain mocked): /slow → `status_reason: "timeout"`, content = snippet (row 3); /forbidden → `status_reason: "http:403"` (row 4); every hit yields non-empty content (SC-004)
- [X] T012 [P] [US2] Write failing integration test for the overall bound (research.md D6 row 11): with test-config `overall_timeout_s` reduced, slow pages end as `fallback` with `status_reason: "cut-off-at-overall-bound"` — the call never exceeds the bound (FR-014)

### Implementation for User Story 2

- [X] T013 [US2] Implement extraction/grouping in src/agentic_rag_mcp/search/web/research.py per research.md D5: Block/PageSection/ScrapeResult per data-model.md — sections from h2/h3, blocks in document order, paragraphs >30 chars, img/figure real src only, urljoin, per-page bound + truncation flag
- [X] T014 [US2] Implement bounded-parallel fetching in src/agentic_rag_mcp/search/web/research.py per research.md D3: ThreadPoolExecutor(`max_concurrent = 4`), per-page `fetch_timeout_s = 15.0`, overall cut-off honoring T012
- [X] T015 [US2] Wire scraping into `web_research` v2 in src/agentic_rag_mcp/server.py: hits gain `scrape` (ScrapeResult with 4-state status + reasons) and `content` (bounded grouped text or the marked snippet fallback) per contracts/web-research-tool.md; extend the contract tests to v2 (schema + fallback invariants)
- [X] T016 [US2] Upgrade the ask pipeline's live-web evidence in src/agentic_rag_mcp/agents/reflexion.py + src/agentic_rag_mcp/server.py wiring per FR-012: grouped `content` replaces the single-page fetch enrichment (internal shape per data-model.md — no render); update tests/unit/test_reflexion_graph.py web-evidence expectations

**Checkpoint**: US1 + US2 complete — grouped research live end to end with every fallback path tested

---

## Phase 5: User Story 3 — Human-Readable Rendering (Priority: P3)

**Goal**: `render_html` — a standalone artifact mirroring the grouped structure, returned inline

**Independent Test**: Save the artifact, open in a browser: title, source link, sections in the same order as `sections` (quickstart.md S1 render check; SC-006)

### Tests for User Story 3

- [X] T017 [P] [US3] Write failing unit tests tests/unit/test_research_render.py (research.md D6 row 14): artifact contains title, source link, sections in order with inline text + images; fallback hits show the snippet with a visible marker; per-page bound respected

### Implementation for User Story 3

- [X] T018 [US3] Implement the renderer in src/agentic_rag_mcp/search/web/research.py per research.md D7 (stdlib string templates, no template engine; FR-010)
- [X] T019 [US3] Add `render_html` to every `web_research` hit in src/agentic_rag_mcp/server.py + extend tests/contract/test_web_research_contract.py with invariant 9 (render mirrors structure)

**Checkpoint**: All three stories complete; the tool matches contracts/web-research-tool.md in full

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, suite, deployment, and validation

- [X] T020 [P] Document the `web_research` tool (11-tool table) and `[web.research]` config in README.md; add the tool row to dify/Chatflow Basic (AgenticRAG Agent).yml instructions
- [X] T021 Full suite green: `.venv/bin/python -m pytest tests/ -q` — all 99 pre-existing tests (incl. untouched tests/contract/test_web_providers.py, SC-001) plus every new suite passing
- [X] T022 Rebuild the sidecar image (docker build -f dify/docker/mcp-server/Dockerfile), redeploy the `agentic-rag` container, refresh Dify's MCP tool cache (Tools → MCP → Agentic RAG → Update), and attach `web_research` to the chatflow's Agent node
- [X] T023 Run quickstart.md S1–S6 end to end against the deployed sidecar and record results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001–T003; T002/T003 parallel
- **Foundational (Phase 2)**: depends on T001 — BLOCKS all stories (T004→T005, T006→T007; the two pairs parallel)
- **User Stories (Phases 3–5)**: depend on Phase 2. US2 depends on US1's tool skeleton (T009); US3 depends on US2's ScrapeResult. Test-authoring within US2/US3 ([P] tasks) can start once Phase 2 lands
- **Polish (Phase 6)**: after all stories

### Within Each User Story

- RED tests before their implementations (Constitution II; the user's binding note)
- Extraction before fetching (T013→T014), fetching before tool wiring (T014→T015), wiring before the ask upgrade (T015→T016)

### Parallel Opportunities

- T002 + T003; T004 + T006 (then T005 + T007); T008 + T010 + T011 + T012 (all RED authoring, different files); T017 alongside US2 implementation

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 + Phase 2 → provenance-carrying chain + guarded fetch, tested
2. Phase 3 (US1) → `web_research` search surface live, contract-tested
3. **STOP and VALIDATE**: quickstart.md S3 (web_search frozen) + S1 search fields

### Incremental Delivery

1. + US2 → grouped extraction with every fallback path (the feature's core value)
2. + US3 → inline rendered artifact
3. Polish → docs, Dify cache refresh, chatflow attach, quickstart S1–S6

---

## Notes

- [P] tasks = different files, no dependencies
- Every test task cites its research.md D6 matrix row(s); every implementation cites its FRs — acceptance is the matrix, not vibes (Constitution II)
- Constraints quoted verbatim in task text (bounds, caps, timeouts) — do not re-decide at implementation time
- `web_search`'s existing suite is the canary: if T005 or any wiring breaks it, the change is wrong (FR-002)
