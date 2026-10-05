# Tasks: Agentic RAG MCP Server

**Input**: Design documents from `/specs/001-agentic-rag-mcp/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED — user explicitly requested "create test case and add error handling" (TDD requested by plan.md Decision 13).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- All paths relative to repo root `/home/ubuntu/kilocode/AgenticRAG`

## Path Conventions

Single Python project: `src/agentic_rag_mcp/`, `tests/`, `specs/001-agentic-rag-mcp/fixtures/` per plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory layout per plan.md (`src/agentic_rag_mcp/{ingestion,sources,store,routing,agents,search/web}`, `tests/{unit,contract,integration}`, `specs/001-agentic-rag-mcp/fixtures/`)
- [x] T002 Initialize `pyproject.toml` with console script `agentic-rag-mcp`, extras `[audio]` (faster-whisper) and `[graphify]`, dependencies: mcp, cocoindex[full], lancedb, sentence-transformers, langgraph, msal, httpx, pypdf, python-docx, openpyxl, python-pptx
- [x] T003 [P] Configure ruff + black + mypy in `pyproject.toml` and add pre-commit config
- [x] T004 [P] Create test fixture corpus: small PDF, DOCX, XLSX, PPTX, MP3 (speech), corrupt PDF, and sample SQLite DB in `specs/001-agentic-rag-mcp/fixtures/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement config loader `src/agentic_rag_mcp/config.py` — TOML at `~/.config/agentic-rag-mcp/config.toml` (embedding model, iteration budget, provider keys, Laya endpoint/token)
- [x] T006 Implement error taxonomy `src/agentic_rag_mcp/errors.py` — `IngestionError`, `SourceAuthError`, `ProviderError`, `SufficiencyExhausted`, `DecisionLayerUnavailable`; mapping to MCP error results with machine-readable `code` field (`NotFound|AuthRequired|ProviderUnavailable|ParseFailed|BudgetExhausted|FeatureDisabled`); stack traces never returned over the wire
- [x] T007 Implement base store `src/agentic_rag_mcp/store/state.py` — SQLite tables for documents (`content_hash` unique per data-model.md), origins, sources (health enum `healthy|degraded|down` + `health_reason`), sessions
- [x] T008 [P] Implement LanceDB wrapper `src/agentic_rag_mcp/store/vectordb.py` — collections, chunk upsert, chunk invalidation by `document_id` ("on Document content change → old Chunks invalidated (delete), new Chunks inserted")
- [x] T009 [P] Implement embedding service `src/agentic_rag_mcp/search/vector.py` (embedding half) — local sentence-transformers `all-MiniLM-L6-v2`, batch encode
- [x] T010 [P] Implement MCP server shell `src/agentic_rag_mcp/server.py` + `__main__.py` — FastMCP stdio, tool registration stubs, structured JSON request logging with correlation IDs, `status` tool
- [x] T011 [P] Implement content-hash dedup `src/agentic_rag_mcp/ingestion/dedup.py` — SHA-256 of normalized text; merge `origins[]` on collision; drop document only when last OriginRef removed
- [x] T012 [P] Implement document/audio parsers `src/agentic_rag_mcp/ingestion/parsers.py` + `transcribe.py` — pypdf/python-docx/openpyxl/python-pptx extraction; faster-whisper behind `[audio]` extra; corrupt/encrypted/no-speech ⇒ `status: failed|skipped` with reason, never blocks batch
- [x] T013 [P] Unit tests for errors, state store, dedup, parsers in `tests/unit/` — assert corrupt-PDF fixture is skipped with reason; assert dedup merges identical-content documents from two locators

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Ask a question and get a sourced answer (Priority: P1) 🎯 MVP

**Goal**: Client asks a natural-language question via MCP; system retrieves from ingested local documents and answers with citations.

**Independent Test**: Ingest fixtures folder → call `ask` → answer cites the correct source document; unknown question ⇒ "no relevant information" response (no fabrication).

### Tests for User Story 1 ⚠️ (write FIRST, must FAIL)

- [x] T014 [P] [US1] Contract test for `ask`, `search`, `sources.add`, `sources.list` tool schemas in `tests/contract/test_mcp_tools.py` against `contracts/mcp-tools.md`
- [x] T015 [P] [US1] Integration test in `tests/integration/test_fast_path.py` — stdio session with real LanceDB tmp dir + local embedding model; assert citation correctness and `< 10 s` fast-path budget
- [x] T016 [P] [US1] Unit test for heuristic fallback classifier `tests/unit/test_fallback_classifier.py` — Laya unreachable ⇒ classification `deliberative`/fallback noted in trace, answer still returned

### Implementation for User Story 1

- [x] T017 [P] [US1] Implement local-folder connector `src/agentic_rag_mcp/sources/local_folder.py` — watch/add/remove; sync_state mtimes; per-file failure isolation
- [x] T018 [US1] Implement CocoIndex [full] ingestion pipeline `src/agentic_rag_mcp/ingestion/pipeline.py` — change detection (add/update/delete) → parse/transcribe → dedup → embed → LanceDB upsert/invalidate; records per-item ingestion status
- [x] T019 [P] [US1] Implement web-provider adapter interface `src/agentic_rag_mcp/search/web/base.py` (needed by `ask` contract even if no provider configured)
- [x] T020 [US1] Implement Laya decision-layer client `src/agentic_rag_mcp/routing/laya.py` — call Laya local MCP/HTTP for fast/deep classification; timeout ⇒ `DecisionLayerUnavailable` → fallback path (FR-012)
- [x] T021 [P] [US1] Implement heuristic fallback classifier `src/agentic_rag_mcp/routing/fallback.py` — keyword/length/structure heuristics; default `deliberative`
- [x] T022 [US1] Implement fast path in `server.py` — vector_search over LanceDB → synthesize answer with citations (`citations[].kind/ref/title` per contract); empty retrieval ⇒ explicit "no relevant information" (US1 acceptance #2)
- [x] T023 [US1] Wire `sources.add/remove/list/sync` in `server.py` — local_folder type only; manual `sources.sync` returns `{added, updated, deleted, skipped[]}` counts
- [x] T024 [US1] Error handling for US→trace surface: degraded sources included in every `ask` response; stack traces logged server-side only

**Checkpoint**: quickstart Scenario 1 passes end-to-end

---

## Phase 4: User Story 2 - Keep the knowledge base up to date automatically (Priority: P1)

**Goal**: Add/change/delete in watched sources reflected in retrieval automatically — no manual full rebuild (FR-004), freshness ≤ 5 min (SC-002).

**Independent Test**: Add doc → searchable within window; edit doc → new content answers; delete doc → absent from results.

### Tests for User Story 2 ⚠️ (write FIRST, must FAIL)

- [x] T025 [P] [US2] Integration test `tests/integration/test_incremental.py` — add/edit/delete fixture files, assert poll-based sync picks each up and LanceDB chunks are upserted/invalidated correctly
- [x] T026 [P] [US2] Integration test `tests/integration/test_remote_sources.py` — mocked MSAL/Graph: OneDrive + SharePoint connectors list/ingest files; expired token ⇒ `degraded` with `auth_expired`, other sources keep syncing

### Implementation for User Story 2

- [x] T027 [P] [US2] Implement file-watcher loop `src/agentic_rag_mcp/ingestion/watchers.py` — mtime/hash change detection feeding the incremental pipeline
- [x] T028 [P] [US2] Implement SQLite source connector `src/agentic_rag_mcp/sources/sqlite_source.py` — read-only; user table/column→text template config; per-row content hash change detection (FR-002)
- [x] T029 [US2] Implement MSAL auth helper `src/agentic_rag_mcp/sources/graph_auth.py` — delegated per-user OAuth, device-code flow, disk token cache; never stores secrets in config (Q4 clarification)
- [x] T030 [P] [US2] Implement OneDrive connector `src/agentic_rag_mcp/sources/onedrive.py` — Graph delta sync, high-water mark in sync_state (FR-003)
- [x] T031 [P] [US2] Implement SharePoint connector `src/agentic_rag_mcp/sources/sharepoint.py` — Graph sites delta sync (FR-003)
- [x] T032 [US2] Wire remote connectors into `sources.add/list/sync` in `server.py`; auth failure ⇒ `SourceAuthError` → `health: degraded/auth_expired`, batch continues (edge case)

**Checkpoint**: quickstart Scenario 2 passes; mocked-Graph contract test green

---

## Phase 5: User Story 3 - Deep research on complex questions (Priority: P2)

**Goal**: LangGraph ReAct loop: decompose complex questions, route sub-tasks to vector/SQL/web/tools, check sufficiency, loop within budget, low-confidence flag on exhaustion (FR-013/014/015/017).

**Independent Test**: Question needing ≥ 2 source types ⇒ trace shows ≥ 2 tools, per-sub-task citations, synthesized answer; unanswerable question stops at budget with `confidence: low` and no fabricated citations.

### Tests for User Story 3 ⚠️ (write FIRST, must FAIL)

- [x] T033 [P] [US3] Unit test for sufficiency evaluator `tests/unit/test_sufficiency.py` and planner heuristics in `src/agentic_rag_mcp/routing/planner.py`
- [x] T034 [P] [US3] Integration test `tests/integration/test_deep_path.py` — forced deliberative mode (`mode: "deep"`) over fixtures + SQLite source; assert trace tools, budget exhaustion ⇒ `confidence: low` + `BudgetExhausted` surfaced in metadata
- [x] T035 [P] [US3] Contract test `tests/contract/test_laya_client.py` — mocked Laya API classification responses; unavailable ⇒ fallback

### Implementation for User Story 3

- [x] T036 [US3] Implement planner `src/agentic_rag_mcp/routing/planner.py` — LLM-based sub-task decomposition with tool choices (`vector_search|sql_query|web_search|onedrive|sharepoint|graphify`)
- [x] T037 [P] [US3] Implement agent tools `src/agentic_rag_mcp/agents/tools.py` — vector_search, sql_query (read-only against configured SQLite sources), source-scoped fetchers
- [x] T038 [P] [US3] Implement sufficiency node `src/agentic_rag_mcp/agents/sufficiency.py` — evidence evaluation; `satisfied|exhausted` outcome per data-model.md
- [x] T039 [US3] Implement LangGraph reflection graph `src/agentic_rag_mcp/agents/graph.py` — plan → route → retrieve → sufficiency → loop (bounded) → synthesize with provenance; records reasoning/tool steps per session (FR-015/016)
- [x] T040 [US3] Wire deep path via Laya/heuristic classification into `ask` in `server.py`; honor `mode` and `max_iterations` inputs from contract

**Checkpoint**: quickstart Scenario 3 passes

---

## Phase 6: User Story 4 - Search the live web alongside private data (Priority: P3)

**Goal**: Real-time web search via pluggable providers; web citations distinguished (`kind: "web" + URL`); provider failure falls back without breaking local answers (SC-005).

**Independent Test**: Question about recent public event (absent locally) ⇒ answer cites web URLs; provider poisoned ⇒ `degraded_sources` names it, local-only answer still returned.

### Tests for User Story 4 ⚠️ (write FIRST, must FAIL)

- [x] T041 [P] [US4] Contract tests for Tavily/Exa/SearXNG adapters in `tests/contract/test_web_providers.py` — normalized result shape, timeout/error ⇒ `ProviderError`
- [x] T042 [P] [US4] Integration test `tests/integration/test_web_fallback.py` — provider down ⇒ fallback per SC-005 (100% of failure-injection assertions)

### Implementation for User Story 4

- [x] T043 [P] [US4] Implement Tavily adapter `src/agentic_rag_mcp/search/web/tavily.py`
- [x] T044 [P] [US4] Implement Exa adapter `src/agentic_rag_mcp/search/web/exa.py`
- [x] T045 [P] [US4] Implement SearXNG adapter `src/agentic_rag_mcp/search/web/searxng.py` (self-hosted URL config)
- [x] T046 [US4] Wire web_search tool with provider fallback order into `agents/tools.py` and planner routing in `server.py`; ensure web citations carry `kind: "web"`

**Checkpoint**: quickstart Scenario 4 passes

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Optional graph layer, hardening, validation

- [x] T047 [P] Implement optional Graphify wrapper `src/agentic_rag_mcp/search/graphify_search.py` + `graph.query` tool — disabled by default; disabled ⇒ `FeatureDisabled` error per contract
- [x] T048 [P] Unit-test coverage pass in `tests/unit/` — target ≥ 80% on routing/agents/ingestion modules
- [x] T049 [P] Error-handling audit against spec Edge Cases — every edge case has ≥ 1 asserting test (corrupt/encrypted file, no-speech audio, cross-source duplicate, expired credential, concurrent queries, Laya down, budget exhaustion)
- [x] T050 Run all quickstart.md scenarios (1–6) as release validation and record outcomes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — BLOCKS all stories
- **US1 (Phase 3)**: after Foundational — MVP
- **US2 (Phase 4)**: after Foundational; shares pipeline with US1 (T018) — sequential after US1 for the same files recommended
- **US3 (Phase 5)**: after US1 (needs vector_search + Laya client); independent of US2
- **US4 (Phase 6)**: after US3 (web_search plugs into agent tools)
- **Polish (Phase 7)**: after all desired stories

### User Story Dependencies

- **US1 (P1)**: none beyond Foundational
- **US2 (P1)**: reuses pipeline/connectors from US1
- **US3 (P2)**: needs US1 tools + Laya client; testable alone with `mode: "deep"`
- **US4 (P3)**: needs US3 tool-routing

### Parallel Opportunities

- T003/T004 (setup) in parallel
- T008–T013 (foundational, different files) in parallel
- T014–T016, T017/T019/T021 (US1 tests & leaf modules) in parallel
- T025/T026 tests in parallel; T030/T031 connectors in parallel
- T033–T035 tests in parallel; T037/T038 in parallel
- T041–T045 (all three web adapters + tests) in parallel

## Parallel Example: User Story 1

```bash
# Tests (write first, in parallel):
Task: "Contract test for MCP tools in tests/contract/test_mcp_tools.py"
Task: "Integration test fast path in tests/integration/test_fast_path.py"
Task: "Unit test fallback classifier in tests/unit/test_fallback_classifier.py"

# Leaf modules in parallel:
Task: "Implement local-folder connector in src/agentic_rag_mcp/sources/local_folder.py"
Task: "Implement web-provider base in src/agentic_rag_mcp/search/web/base.py"
Task: "Implement heuristic fallback classifier in src/agentic_rag_mcp/routing/fallback.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational (CRITICAL)
2. Phase 3 US1 → validate with quickstart Scenario 1
3. Demo: locally-ingested docs answering questions with citations over stdio MCP

### Incremental Delivery

1. + US2 → freshness/remote connectors validated (Scenario 2)
2. + US3 → deep research (Scenario 3)
3. + US4 → web search (Scenario 4)
4. Phase 7 → optional Graphify, coverage audit, full quickstart validation
