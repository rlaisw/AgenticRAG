# Implementation Plan: Specialty Web Search — Profile-Scoped Domain Search

**Branch**: `005-specialty-search` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-specialty-search/spec.md`

## Summary

A new `specialty_search(query, profile, limit)` MCP tool that scopes web search results to pre-defined authoritative domains via `site:` query-string operators, plus a companion `specialty_profiles()` listing tool. Profiles live in a user-managed JSON file (`~/.config/agentic-rag-mcp/specialty_profiles.json`), hot-reloaded on every call. The Dify agent calls both `specialty_search` and `web_search` for domain-specific questions and synthesizes — specialty as primary authority, general as supplementary. Zero new dependencies; the existing provider chain handles everything.

## Technical Context

**Language/Version**: Python 3.12 (project venv)
**Primary Dependencies**: No new deps — existing mcp SDK 1.30, httpx; JSON parsing is stdlib (`json.load`)
**Storage**: No new storage — profiles read from a JSON file at request time (hot-reload)
**Testing**: pytest — new unit tests for profile loading, site filtering, query construction; contract test for response shape; integration over the live chain
**Target Platform**: Linux host venv + Docker sidecar (profiles file mounted via existing config volume)
**Project Type**: MCP server (stdio / stateless HTTP sidecar)
**Performance Goals**: same as `web_search` (the chain is identical; only the query string differs)
**Constraints**: existing tool response shapes frozen (Constitution I / SC-004); honest empty/error states (Constitution IV)

## Constitution Check

| Principle | Status | Evidence |
|---|---|---|
| I. Contract Preservation | PASS | `specialty_search` returns the same shape as `web_search` (title/url/snippet) + engine provenance; all existing tools unchanged; SC-004 enforces via the existing 131-test suite |
| II. Tests-First | PASS | RED tests before implementation: profile loading (missing file, malformed, case-insensitive), site filter (substring match), query construction, contract shape |
| III. Minimal Dependencies | PASS | Zero new dependencies — stdlib `json`, existing chain |
| IV. Honest Answers | PASS | FR-004 (missing file), FR-007 (invalid profile), FR-008 (empty sites) all return explicit errors; FR-006 filters non-matching URLs; empty results honest |
| V. Spec-Driven Replacement | PASS | purely additive — no replacement, no retirement |

## Project Structure

### Documentation (this feature)

```text
specs/005-specialty-search/
├── plan.md              # This file
├── research.md         # Phase 0 output
├── data-model.md       # Phase 1 output
├── contracts/specialty-search-tool.md
├── quickstart.md       # Phase 1 output
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/agentic_rag_mcp/
├── server.py                    # + specialty_search + specialty_profiles MCP tools
├── config.py                    # + [web.specialty] file path config
└── search/web/
    └── specialty.py             # NEW: profile loader (JSON, hot-reload),
                                 #   query constructor (site: prefix),
                                 #   domain filter (substring match)

tests/
├── unit/
│   └── test_specialty.py        # profile loading, case-insensitivity, query construction,
│                               # domain filter (substring), error paths
├── contract/
│   └── test_specialty_contract.py # response shape pin, frozen tool canary
└── integration/
    └── test_specialty_integration.py # live chain with site: scoping, honest errors

dify/Chatflow Basic (AgenticRAG Agent).yml  # + specialty_search + specialty_profiles tool entries
```

### User-managed file (not committed to the repo)

```text
~/.config/agentic-rag-mcp/specialty_profiles.json
```

## Complexity Tracking

No constitution violations. The only design decision worth noting: the profile loader reads the JSON file on EVERY `specialty_search`/`specialty_profiles` call — a deliberate choice for hot-reload semantics. File reads are ~microseconds; no caching needed (ponytail: cache only if profiling shows a problem).
