# Implementation Plan: Grouped Web Research — Multi-Engine Search with Outline-Preserving Page Scraping

**Branch**: `003-web-search-scrape` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-web-search-scrape/spec.md`

**User note (binding)**: the plan MUST include creating test cases and adding error handling as first-class deliverables — every fallback/error path gets a runnable test (matches Constitution II; see research.md D6 for the test strategy and error-handling matrix).

## Summary

Extend the existing web-provider chain (kept — litellm rejected with evidence) with grouped web research: a new `web_research(query, limit)` MCP tool that searches via the same chain, then fetches each result page (SSRF-guarded, bounded-parallel, per-page timeout), extracts sections preserving document order (heading → text → belonging image → text), bounds content per page, renders a standalone HTML artifact returned inline, and marks honest snippet fallbacks everywhere. The `ask` pipeline's live-web evidence upgrades to the same grouped content (FR-012). `web_search`'s contract stays byte-identical.

## Technical Context

**Language/Version**: Python 3.12 (project venv, package `agentic-rag-mcp`)

**Primary Dependencies**: existing — mcp SDK 1.30 (FastMCP), httpx (reused for page fetching — see research D1), langgraph; **new (the only ones)**: `beautifulsoup4` + `lxml` for outline extraction (research D2). **No litellm** (decided — spec Clarifications).

**Storage**: none new — research results are per-request and ephemeral; the rendered artifact travels inline in the response (FR-010). No LanceDB/state changes.

**Testing**: pytest (currently 99 tests). Three new layers per research D6: unit (extraction fixtures, SSRF guard, renderer), integration (`web_research` end-to-end over local fixture pages with the engine chain mocked — no live web in CI), contract (`web_search` shape frozen + `web_research` response schema pinned). **Error-handling tests are first-class**: one test per fallback path (timeout, JS-only, HTTP error, private-address block, oversized page, engine-down, all-engines-down).

**Target Platform**: Linux host venv + the deployed Docker sidecar (on Dify networks — hence the SSRF guard, FR-013).

**Project Type**: library + MCP server (stdio / stateless HTTP sidecar).

**Performance Goals**: typical 3-page `web_research` call < 30 s end to end (FR-014 / SC-007) via bounded-parallel page fetches (research D3); per-page timeout 15 s default; per-page content bound default 6,000 chars.

**Constraints**: `web_search` response byte-identical (Constitution I / FR-002); no new search dependencies; scraping must not fabricate — every hit yields grouped sections or a marked fallback (FR-008).

**Scale/Scope**: single-user; research bounded by `limit` (default 3, max 5).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Contract Preservation | PASS | `web_search` frozen (FR-002, SC-001); `web_research` is additive; ask evidence changes are internal (FR-012) |
| II. Tests-First | PASS (binding per user note) | Plan mandates test tasks before implementation tasks; error-handling matrix (research D6) enumerates the required tests |
| III. Minimal Dependencies | PASS | Only bs4+lxml added (new capability); httpx reused over `requests`; litellm rejected; renderer is stdlib string templates (no template engine) |
| IV. Honest Answers | PASS | Every fallback is explicit and marked — blocked pages, timeouts, JS-only pages, truncated pages, empty results (FR-008/013/014) |
| V. Spec-Driven Replacement | PASS | FR-012's replacement of the fetch enrichment is spec'd; the chain itself is retained, not rewritten |

No violations. Re-checked post-Phase-1 design — still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-web-search-scrape/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── web-research-tool.md
├── quickstart.md        # Phase 1 output
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/agentic_rag_mcp/
├── server.py                          # + web_research MCP tool (FR-011); ask wiring unchanged
├── config.py                           # + [web.research] section: max_pages, per_page_chars,
│                                       #   fetch_timeout_s, overall_timeout_s (30), max_concurrent
├── search/web/
│   ├── base.py                         # EXTENDED: engine provenance in results (FR-001), URL dedup (FR-004)
│   ├── research.py                     # NEW: ScrapeResult/PageSection extraction (bs4+lxml),
│   │                                   #   SSRF guard, bounded-parallel fetch, renderer (FR-005..010, 013, 014)
│   └── (searxng/tavily/exa adapters)   # UNCHANGED
├── agents/reflexion.py                 # AMENDED: live-web evidence = grouped sections (FR-012)
└── …

tests/
├── unit/
│   ├── test_research_extraction.py     # NEW: grouping order, data-URI skip, urljoin, truncation (fixtures)
│   ├── test_research_guard.py          # NEW: SSRF — private/loopback/link-local refused (resolver mocked)
│   └── test_research_render.py         # NEW: artifact mirrors sections in order
├── integration/
│   └── test_web_research.py            # NEW: end-to-end over local fixture pages (engine chain mocked);
│                                       #   ask live_web grouped-evidence upgrade; latency smoke (<30s path)
├── contract/
│   └── test_web_research_contract.py   # NEW: response schema pin; web_search shape frozen (extends
│                                       #   existing test_web_providers.py assertions)
```

**Structure Decision**: research code lives beside the providers in `search/web/research.py` (one new module; no new package); the SSRF guard is a function inside it (`# ponytail` noted for possible later extraction if `fetch_url` adopts it — out of scope per spec).

## Complexity Tracking

No constitution violations to justify. Watch items: bs4+lxml is the only new dependency pair (justified: outline extraction is a new capability; stdlib `html.parser` is too fragile for figure/img/data-src handling); lxml binary wheel adds ~5 MB to the Docker image.
