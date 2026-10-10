# Specification Quality Checklist: OneDrive Ingestion — Full Pipeline with Auto-Update

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-10
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — Graph API/MSAL named only as existing foundation context, not as FRs
- [x] Focused on user value and business needs (cloud files searchable, auto-update)
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable (5 files ingested, ≤5 min watcher, eviction verified)
- [x] Success criteria are technology-agnostic (no framework names in SCs)
- [x] All acceptance scenarios are defined (12 total across 3 stories)
- [x] Edge cases are identified (7)
- [x] Scope is clearly bounded (SharePoint, shared-with-me, upload/write-back out of scope)
- [x] Dependencies and assumptions identified (6)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows (add + auth, auto-update, credential lifecycle)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Constitution Compliance (ratified 2026-10-08)

- [x] **I. Contract Preservation**: FR-012 pins all existing tool shapes unchanged; new source type + `sources_auth` tool are additive
- [x] **II. Tests-First**: plan must mandate RED tests for every sync path (new/changed/deleted, auth expiry, unsupported formats, size limits)
- [x] **III. Minimal Dependencies**: no new dependencies — reuses msal (already installed), httpx (already installed), the existing pipeline
- [x] **IV. Honest Answers**: FR-013 — every skip/error/fallback produces explicit reasons; auth failures never block other sources
- [x] **V. Spec-Driven Replacement**: this ADDS a new source type; no existing code is replaced (the pipeline extends, doesn't rewrite)

## Notes

- Validation pass 1 (2026-10-10): all items pass. Zero NEEDS CLARIFICATION markers.
- Gap analysis performed: the existing code has `GraphAuth` (MSAL device flow) and `OneDriveSource.files()` (top-level listing) but NO pipeline integration, NO download, NO recursive traversal, NO watcher support, and NO server wiring. This spec covers those gaps.
- The existing `sources/graph_auth.py` and `sources/onedrive.py` are foundation code from spec 001 — this feature wires them into the full ingestion pipeline rather than rewriting them.
- Candidate clarify decisions (reasonable defaults exist for all):
  1. Auth flow: device code flow (already implemented) vs. browser redirect — device code is simpler for a headless server; the existing implementation uses it.
  2. File listing scope: root folder only vs. recursive — recursive is the useful default (user has nested folders); configurable via `include_subfolders`.
  3. Change detection: Graph API metadata (last_modified + item_id) vs. full download-and-hash — metadata is cheaper and already available; content-hash dedup still applies after download.
- Validation pass 2 (2026-10-10, second clarify pass): two gaps found and resolved:
  1. **Pagination gap (FR-014 added)**: the existing `OneDriveSource.files()` returns only the first page (~200 items); the spec now requires pagination via `@odata.nextLink` on ALL listing calls — a correctness requirement, not a user decision.
  2. **Delta queries (FR-009 updated)**: the Graph API's delta endpoint is the sync mechanism (user decision: Option A) — one API call for all changes, handles adds/modifies/deletes natively, paginates transparently, and is Microsoft's recommended sync pattern. The `OneDriveSyncState` entity updated to use a delta-link cursor instead of item-ID diffing.
