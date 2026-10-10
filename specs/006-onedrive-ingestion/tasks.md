---
description: "Task list for feature implementation"
---

# Tasks: OneDrive Ingestion — Full Pipeline with Auto-Update

**Input**: Design documents from `specs/006-onedrive-ingestion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/onedrive-source.md, quickstart.md

**Tests**: INCLUDED — Constitution II + the user's standing binding note. Every research.md D7 error-matrix row gets a runnable test. No live Graph API in CI — all tests mock httpx responses.

**Organization**: Tasks grouped by user story; US1 (add + initial sync) is the MVP.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (No story label — shared foundation)

- [X] T001 Extend src/agentic_rag_mcp/sources/onedrive.py with pagination (`@odata.nextLink` following), delta query support (`GET /me/drive/root/delta` with optional cursor), file download (via `@microsoft.graph.downloadUrl`), and a `sync(auth, config, state) -> dict` method that returns per-item stats — per research.md D1/D2/D4 and data-model.md lifecycle

---

## Phase 2: User Story 1 — Add + Authenticate + Initial Sync (Priority: P1) 🎯 MVP

**Goal**: `sources_add(type: "onedrive")` works end-to-end: register, authenticate (device flow), list files, download, parse, embed into LanceDB

**Independent Test**: Add a OneDrive source with a mocked Graph API → files are listed (with pagination), downloaded, parsed, and embedded; ask a question → answer cites the OneDrive file (quickstart.md S1-S3)

### Tests for User Story 1 (all RED before implementation)

- [X] T002 [P] [US1] Write failing unit tests tests/unit/test_onedrive.py for src/agentic_rag_mcp/sources/onedrive.py: pagination follows @odata.nextLink across multiple pages (FR-014); delta query parses adds/modifies/deletes; recursive folder traversal via child items; file download via pre-authenticated downloadUrl; size cap >50 MB skipped with reason (FR-008); unsupported formats skipped with reason (FR-007); empty drive returns healthy with 0 files; auth error raises SourceAuthError
- [X] T003 [P] [US1] Write failing contract tests tests/contract/test_onedrive_contract.py: sources_add(type: "onedrive") with token returns status ok + sync stats; without token returns needs_auth + sign-in hint (FR-001/002); sources_auth returns sign_in_url + user_code (FR-003); sources_auth on healthy source returns already_authenticated; sources_list includes onedrive type; frozen tool canary (152-test suite unchanged — SC-005)
- [X] T004 [P] [US1] Write failing integration tests tests/integration/test_onedrive_integration.py: build_server with mocked Graph API — add source → mock auth → sync → files in LanceDB (SC-001); pagination across 3 pages of results; nested folder files found; delta-link cursor persisted in sync_state

### Implementation for User Story 1

- [X] T005 [US1] Add `sync_onedrive(source_id, source, auth)` to src/agentic_rag_mcp/ingestion/pipeline.py: get token → delta or initial listing → classify items (new/changed/deleted) → download supported files via downloadUrl → parse through the existing parser chain → dedup by content-hash → chunk → embed into LanceDB → persist delta-link cursor → return stats per FR-005/006/007/008/009
- [X] T006 [US1] Wire `sources_add(type: "onedrive")` in src/agentic_rag_mcp/server.py: validate config (client_id required, folder_path default "/", include_subfolders default true, max_file_size_mb default 50 per data-model.md); check token cache; if token exists → healthy + trigger initial sync; if not → needs_auth + sign-in hint per FR-001/002

**Checkpoint**: MVP — OneDrive source registered, authenticated, and initial sync ingests files into LanceDB

---

## Phase 3: User Story 2 — Auto-Update via Delta Sync (Priority: P1)

**Goal**: The 5-minute watcher syncs OneDrive sources using delta queries — new files ingested, edited files re-embedded with old chunks evicted, deleted files' chunks removed

**Independent Test**: Mock a delta response with 1 add + 1 modify + 1 delete → sync → new file searchable, edited file has new content, deleted file's chunks evicted (SC-002/003)

### Tests for User Story 2

- [X] T007 [P] [US2] Write failing integration tests tests/integration/test_onedrive_integration.py (extend T004): delta sync with cursor returns only changed items; new file ingested within one cycle (SC-002); edited file's old chunks evicted and new content replaces them (SC-003 — spec-002 eviction fix); deleted file's chunks removed from LanceDB; auth expiry mid-sync marks source degraded, other sources continue (SC-004)

### Implementation for User Story 2

- [X] T008 [US2] Add the onedrive case to src/agentic_rag_mcp/ingestion/watchers.py sync_once(): call sync_onedrive with the delta cursor; catch SourceAuthError → mark degraded "sign-in required"; catch ProviderError → mark degraded with error; never re-raise (isolation per FR-010); call sync_onedrive also from server.py sources_sync for manual sync (FR-011)
- - [X] T009 [US2] Make T007 pass (run and fix until green)

**Checkpoint**: Auto-update working — watcher detects OneDrive changes via delta queries and keeps LanceDB current

---

## Phase 4: User Story 3 — Credential Lifecycle (Priority: P2)

**Goal**: `sources_auth` tool completes the device sign-in flow non-blocking; users can re-authenticate expired tokens

**Independent Test**: Call sources_auth on a needs_auth source → get URL+code → mock token acquisition → source becomes healthy (SC-004)

### Tests for User Story 3

- [X] T010 [P] [US3] Write failing contract tests tests/contract/test_onedrive_contract.py (extend T003): sources_auth on needs_auth source returns sign_in_url + user_code; sources_auth on healthy source returns already_authenticated; sources_auth on non-existent source_id returns honest error

### Implementation for User Story 3

- [X] T011 [US3] Add `sources_auth(source_id)` MCP tool to src/agentic_rag_mcp/server.py per contracts/onedrive-source.md: initiate MSAL device flow via GraphAuth.device_sign_in() in a background thread (non-blocking per research.md D3); return {status: "sign_in_required", sign_in_url, user_code} immediately; on already-authenticated return {status: "already_authenticated"}; background thread saves token → marks source healthy → triggers sync

**Checkpoint**: All three stories complete — OneDrive source fully functional with auth, auto-update, and re-auth

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T012 [P] Update README.md: add OneDrive to the source types, add sources_auth to the tool table (14 tools), document the Azure AD prerequisite
- [X] T013 [P] Update dify/Chatflow Basic (AgenticRAG Agent).yml: add sources_auth tool entry (14 tools) + update instruction: "For OneDrive setup, call sources_add(type 'onedrive'), relay the sign-in URL and code from sources_auth, then check status"
- [X] T014 Full suite green: `.venv/bin/python -m pytest tests/ -q` — all 152 pre-existing + new onedrive tests passing
- [X] T015 Rebuild sidecar image, redeploy, refresh Dify MCP tool cache (13→14 tools)
- [X] T016 Commit all changes and push to GitHub

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 (the extended OneDriveSource) — blocks all stories
- **US1 (Phase 2)**: T002+T003+T004 (RED, parallel) → T005 → T006 (pipeline before server wiring)
- **US2 (Phase 3)**: T007 (RED) → T008+T009 — depends on T005 (pipeline method)
- **US3 (Phase 4)**: T010 (RED) → T011 — depends on T006 (source_id exists)
- **Polish (Phase 5)**: after all stories

### Parallel Opportunities

- T002 + T003 + T004 (all RED tests, different files)
- T007 + T010 (different test extensions)
- T012 + T013 (different files)

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (T001) → OneDriveSource extended with pagination, delta, download
2. Phase 2 (T002–T006) → add + auth + initial sync working
3. **STOP and VALIDATE**: quickstart.md S1–S3 (add source, sign in, files searchable)

### Incremental Delivery

1. + US2 → auto-update via delta queries, eviction verified
2. + US3 → sources_auth tool, re-auth flow
3. Polish → docs, chatflow, deploy, commit

---

## Notes

- [P] tasks = different files, no dependencies
- Every test cites its research.md D7 error-matrix row / FR / SC — acceptance is the matrix
- The most complex task is T001 (extend OneDriveSource) — pagination + delta + download + sync method in one file
- The non-blocking sources_auth (T011) uses the same background-thread pattern as laya_runtime.warm_up()
- No live Graph API in CI — all tests mock httpx responses; live verification is quickstart S1–S5 (requires a real Azure AD app + OneDrive account)
