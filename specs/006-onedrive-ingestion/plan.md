# Implementation Plan: OneDrive Ingestion — Full Pipeline with Auto-Update

**Branch**: `006-onedrive-ingestion` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-onedrive-ingestion/spec.md`

## Summary

Wire the existing MSAL auth + Graph API listing code into the full ingestion pipeline: add `type: "onedrive"` to `sources_add`, create a `sources_auth` tool for device-code sign-in, add a `sync_onedrive()` pipeline method with recursive folder traversal + pagination, use Graph API **delta queries** for the 5-minute watcher's incremental sync, and download files via their Graph API URLs through the existing parser/embedding chain. Zero new dependencies — reuses `msal` and `httpx` (both installed).

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: No new deps — existing `msal` (auth), `httpx` (HTTP), `mcp` SDK 1.30

**Existing foundation (verified in code)**:
- `sources/graph_auth.py` (53 lines) — `GraphAuth` with MSAL device flow, per-source token cache, silent refresh
- `sources/onedrive.py` (77 lines) — `GraphBase._get()` + `OneDriveSource.files()` (top-level listing only, no pagination, no download, no recursion)
- `ingestion/pipeline.py` — `sync_local_folder()` and `sync_sqlite()`; no `sync_onedrive()`
- `ingestion/watchers.py` — handles `local_folder` and `sqlite` only
- Parsers: PDF, DOCX, XLSX, PPTX (shared by all sources)
- Eviction fix (spec 002): origin re-pointing + orphan chunk deletion

**Graph API endpoints used**:
| Purpose | Endpoint |
|---|---|
| List root children | `GET /me/drive/root/children` (existing, needs pagination fix) |
| List folder children | `GET /me/drive/items/{id}/children` (new, recursive) |
| Delta sync | `GET /me/drive/root/delta` or `GET /me/drive/items/{id}/delta` (new) |
| Download file | `GET {item.downloadUrl}` (direct, pre-authenticated URL) |

**Storage**: No new storage — delta-link cursor stored in the existing state DB's source `sync_state`; token cache at `~/.config/agentic-rag-mcp/tokens/{source_id}.json`

**Testing**: pytest — unit (Graph API mocked), integration (auth flow mocked, pipeline real), contract (response shapes pinned)

**Constraints**: Tool response shapes frozen (Constitution I / FR-012); honest errors everywhere (FR-013); 50 MB file cap (FR-008)

## Constitution Check

| Principle | Status | Evidence |
|---|---|---|
| I. Contract Preservation | PASS | FR-012: new source type + `sources_auth` tool are additive; 152-test suite stays green |
| II. Tests-First | PASS | RED tests for every path: add source, auth flow, sync (delta), pagination, download, eviction, auth expiry, partial sync |
| III. Minimal Dependencies | PASS | Zero new deps — msal + httpx already installed |
| IV. Honest Answers | PASS | FR-013: unsupported formats, oversized files, auth failures, API errors — all explicit reasons; one source's failure never blocks others |
| V. Spec-Driven Replacement | PASS | Extension of the existing pipeline — no replacement, no retirement |

## Project Structure

### Documentation (this feature)

```text
specs/006-onedrive-ingestion/
├── plan.md              # This file
├── research.md         # Phase 0 output
├── data-model.md       # Phase 1 output
├── contracts/onedrive-source.md
├── quickstart.md       # Phase 1 output
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/agentic_rag_mcp/
├── server.py                    # + sources_add "onedrive" wiring + sources_auth tool
├── sources/
│   ├── graph_auth.py            # UNCHANGED (existing MSAL auth is complete)
│   └── onedrive.py              # EXTENDED: recursive listing, pagination, download, delta
├── ingestion/
│   ├── pipeline.py              # + sync_onedrive(source_id, source, auth) method
│   └── watchers.py              # + onedrive case in sync_once()

tests/
├── unit/
│   └── test_onedrive.py         # NEW: pagination, recursion, delta parsing, download mock,
│                                #   config validation, file-size cap, error paths
├── contract/
│   └── test_onedrive_contract.py # NEW: sources_auth response shape, sources_add onedrive
└── integration/
    └── test_onedrive_integration.py # NEW: end-to-end with mocked Graph API
```

### User-managed files (not committed)

```text
~/.config/agentic-rag-mcp/tokens/{source_id}.json    # per-source MSAL token cache
~/.config/agentic-rag-mcp/config.toml                # existing (no new section needed)
```

## Complexity Tracking

No constitution violations. The most complex piece is the **delta sync loop** (Graph API delta → classify items → download+ingest or evict → persist delta-link cursor). The non-blocking `sources_auth` flow (initiate device flow → return URL+code immediately → background thread completes → source transitions to healthy) is the second complexity hotspot.
