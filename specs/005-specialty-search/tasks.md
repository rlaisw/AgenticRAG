---
description: "Task list for feature implementation"
---

# Tasks: Specialty Web Search — Profile-Scoped Domain Search

**Input**: Design documents from `specs/005-specialty-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/specialty-search-tool.md, quickstart.md

**Tests**: INCLUDED — Constitution II + the user's standing binding note ("create test cases and add error handling"). RED tests before implementations; every error path in research.md D6 gets a test.

**Organization**: Tasks grouped by user story; this is a lean list — ~60 lines of new code, zero new dependencies.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Config surface + the JSON profiles file

- [ ] T001 Add `[web.specialty]` to src/agentic_rag_mcp/config.py + DEFAULT_CONFIG per research.md D10: `file = ""` (empty = default path `~/.config/agentic-rag-mcp/specialty_profiles.json`)
- [ ] T002 [P] Create the user-managed profiles file at ~/.config/agentic-rag-mcp/specialty_profiles.json with the 4 confirmed profiles (microsoft, huawei, vibe_coding, ai) per the user's confirmation — see spec Clarifications for the exact JSON content

---

## Phase 2: User Story 1 — Profile-Scoped Search (Priority: P1) 🎯 MVP

**Goal**: `specialty_search(query, profile, limit)` returns domain-scoped results through the existing chain; non-matching URLs filtered; honest errors for every failure path

**Independent Test**: Mock-chain call with a "microsoft" profile → every result URL contains a configured domain (SC-001); invalid profile → honest error with available profiles (SC-003)

### Tests for User Story 1 (all RED before implementation)

- [ ] T003 [P] [US1] Write failing unit tests tests/unit/test_specialty.py for src/agentic_rag_mcp/search/web/specialty.py: profile loading (missing file → error, malformed JSON → error, case-insensitive lookup "Microsoft" = "microsoft", empty sites → error); site normalization (strip https://, path, www., lowercase — data-model.md table); query construction ("site:a OR site:b query" — research.md D3); domain post-filter (substring: "microsoft.com" matches "learn.microsoft.com" — research.md D4); every error path in the D6 matrix
- [ ] T004 [P] [US1] Write failing contract tests tests/contract/test_specialty_contract.py: specialty_search response shape pin (frozen fields title/url/snippet + engine provenance); specialty_profiles response shape; existing tool canary (the 131-test suite's web_search/web_research tests pass unchanged — SC-004)

### Implementation for User Story 1

- [ ] T005 [US1] Implement src/agentic_rag_mcp/search/web/specialty.py per research.md D1-D6 + data-model.md: load_profiles(path) (JSON read per call — hot-reload), normalize_site(entry) (strip scheme/path/www/lowercase), construct_scoped_query(sites, query) ("site:a OR site:b query"), filter_by_domains(results, sites) (substring FR-006), resolve_profile(profiles, name) (case-insensitive FR-003), error responses per D6 matrix
- [ ] T006 [US1] Add `specialty_search` + `specialty_profiles` MCP tools to src/agentic_rag_mcp/server.py per contracts/specialty-search-tool.md: `specialty_search(query, profile, limit=5)` uses search_all with the scoped query + post-filter; `specialty_profiles()` returns the JSON file content verbatim

**Checkpoint**: MVP — specialty search live, contract-tested, all error paths covered

---

## Phase 3: User Story 2 — Integration Tests (Priority: P1)

**Goal**: The tool works end-to-end through the full chain with honest fallbacks

**Independent Test**: Integration with mocked providers: results filtered to matching domains; empty results honest (no auto-fallback); hot-reload: add a profile mid-test → next call sees it (SC-002)

### Tests for User Story 2

- [ ] T007 [P] [US2] Write failing integration tests tests/integration/test_specialty_integration.py: specialty_search via build_server with a FakeProvider returning mixed-domain URLs → only profile-domain results survive the filter; hot-reload: write a new profile to a tmp JSON file → immediately usable on the next call (no restart — SC-002); 0 scoped results → honest empty `[]` (no general fallback — Constitution IV)

### Implementation for User Story 2

- [ ] T008 [US2] Make T007 pass (run and fix until green)

**Checkpoint**: End-to-end verified — scoped results, hot-reload, honest empties

---

## Phase 4: User Story 3 — Dify Agent Integration (Priority: P2)

**Goal**: The Dify agent has the tools attached, the instruction updated, and the chatflow combines specialty + general results

**Independent Test**: Ask the chatflow "How do I configure DKIM in Exchange Online?" → the agent calls specialty_search (→ learn.microsoft.com) AND web_search (→ broader) and synthesizes (SC-005)

### Implementation for User Story 3

- [ ] T009 [P] [US3] Update dify/Chatflow Basic (AgenticRAG Agent).yml: add `specialty_search` + `specialty_profiles` tool entries (frontend 9-key shape) + update the instruction: "For domain-specific questions, call specialty_profiles() first to see available profiles, then call BOTH specialty_search AND web_search — combine results with specialty as primary authority"

**Checkpoint**: Chatflow DSL ready; Dify deployment is in Polish

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T010 [P] Update README.md: specialty_search + specialty_profiles in the tool table (12→13 tools), [web.specialty] config block, example specialty_profiles.json snippet
- [ ] T011 Full suite green: `.venv/bin/python -m pytest tests/ -q` — all 131 pre-existing + new specialty tests passing
- [ ] T012 Create ~/.config/agentic-rag-mcp/specialty_profiles.json on the live host if not already there (T002), rebuild the sidecar image, recreate the container, refresh Dify's MCP tool cache (12→13 tools), verify via quickstart.md S1–S6
- [ ] T013 Commit all changes and push to GitHub

---

## Dependencies & Execution Order

- **Setup**: T001, T002 parallel
- **US1**: T003+T004 (RED, parallel) → T005 → T006 sequential (impl before wiring)
- **US2**: T007 (RED) → T008 (make green) — depends on T005/T006
- **US3**: T009 after T006 (needs the tool to exist)
- **Polish**: T010 parallel with US3; T011–T013 after all stories

### Parallel Opportunities

- T001 + T002; T003 + T004; T007 + T009 + T010 (different files, no deps)

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Setup (T001–T002) → config + profiles file
2. US1 (T003–T006) → specialty_search + specialty_profiles live, contract-tested
3. **STOP and VALIDATE**: quickstart.md S1 (profiles listing) + S2 (scoped search) + S3 (honest errors)

### Incremental Delivery

1. + US2 → integration-verified (hot-reload, honest empties)
2. + US3 → chatflow DSL updated
3. Polish → docs, suite, deploy, commit

---

## Notes

- [P] tasks = different files, no dependencies
- Every test task cites its research.md D-matrix row / FR / SC — acceptance is the matrix
- The tool is ~60 lines of new code (specialty.py) + ~20 lines of MCP wiring (server.py) — the shortest feature so far
- The 4 confirmed profiles (microsoft, huawei, vibe_coding, ai) are created in T002 — the user can add more by editing the JSON file at any time
- The domain filter (FR-006) is the single most important correctness check — SC-001 pins it with 100% substring-match verification
