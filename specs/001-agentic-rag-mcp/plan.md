# Implementation Plan: Agentic RAG MCP Server

**Branch**: `001-agentic-rag-mcp` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-agentic-rag-mcp/spec.md`

## Summary

Build a single-user, stdio-transport **Agentic RAG MCP server** in Python 3.12. Local files (PDF/Office/audio), SQLite databases, OneDrive and SharePoint Online are ingested incrementally through a **CocoIndex [full]** pipeline into a **LanceDB** vector store with local embeddings; **Graphify** provides an optional graph-search layer. A **System 1 / System 2** router (Laya app as the default decision layer with a heuristic fallback) steers simple questions to fast retrieval and complex ones to a **LangGraph ReAct reflection loop** with autonomous planning, tool routing (vector / SQL / web via Tavily‑Exa‑SearXNG), sufficiency checks, and a bounded iteration budget. Testing is pytest-based (unit/contract/integration) with a typed error taxonomy covering every failure edge case in the spec.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `mcp` (FastMCP, stdio), `cocoindex[full]`, `lancedb`, `sentence-transformers` (local embeddings), `langgraph`, `msal` (Graph delegated auth), `pypdf`/`python-docx`/`openpyxl`/`python-pptx`, `faster-whisper` (audio), `httpx` (web search + Laya API), graphify (optional extra)

**Storage**: LanceDB (embedded, file-backed vectors); SQLite (state, sync checkpoints, config metadata); Graphify `graphify-out/` (optional)

**Testing**: pytest — unit (parsers, dedup, heuristics, fallback), contract (MCP tool schemas + mocked providers), integration (stdio end-to-end, fixture corpus)

**Target Platform**: Linux/macOS/Windows local machine (single user); verified on Ubuntu arm64

**Project Type**: MCP server (stdio, host-spawned)

**Performance Goals**: Fast-path answer < 10 s; incremental freshness ≤ 5 min; deep research bounded by iteration budget

**Constraints**: Fully local default (no hosted embedding/transcription APIs required); per-user delegated OAuth for Microsoft; secrets via token cache/keyring only

**Scale/Scope**: Single-user corpus (~10k–100k documents), one MCP host at a time, ≥ 3 web/drive providers behind adapter interfaces

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unamended placeholder template — no constitutional principles are defined, so no gates apply. **GATE: PASS (vacuous).** Recommend running `/speckit.constitution` later to define project principles.

- ✅ Post-design re-check: PASS. No new gates introduced by the design.

## Project Structure

### Documentation (this feature)

```text
specs/001-agentic-rag-mcp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output (validation scenarios incl. error paths)
├── contracts/           # Phase 1 output
│   └── mcp-tools.md     # MCP tool schemas + error surface
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
pyproject.toml                 # pipx-installable, extras: [audio], [graphify]

src/agentic_rag_mcp/
├── __main__.py                # stdio entry point (FastMCP server)
├── config.py                  # ~/.config/agentic-rag-mcp/config.toml loading
├── server.py                  # tool registration: ask, search, sources.*, status, graph.query
├── ingestion/
│   ├── pipeline.py            # CocoIndex [full] flow → LanceDB
│   ├── watchers.py            # local-folder/SQLite change detection
│   ├── parsers.py             # pdf/docx/xlsx/pptx extraction
│   ├── transcribe.py          # faster-whisper (extra: audio)
│   └── dedup.py               # content-hash aggregation (multi-origin docs)
├── sources/
│   ├── base.py                # Source interface, health, sync_state
│   ├── local_folder.py
│   ├── sqlite_source.py       # read-only, row→text templates
│   ├── onedrive.py            # MSAL delegated auth (Graph)
│   └── sharepoint.py          # MSAL delegated auth (Graph sites)
├── store/
│   ├── vectordb.py            # LanceDB collections, chunk upsert/invalidate
│   └── state.py               # SQLite state (documents, origins, sessions)
├── routing/
│   ├── laya.py                # Laya app decision-layer client (local MCP/HTTP)
│   ├── fallback.py            # heuristic System 1/2 classifier
│   └── planner.py             # sub-task decomposition + tool routing
├── agents/
│   ├── graph.py               # LangGraph reflection loop (ReAct)
│   ├── tools.py               # tools: vector_search, sql_query, web_search, drive fns
│   └── sufficiency.py         # evidence-evaluation node + low-confidence flag
├── search/
│   ├── vector.py              # embedding query over LanceDB
│   ├── web/
│   │   ├── base.py            # provider interface
│   │   ├── tavily.py, exa.py, searxng.py
│   └── graphify_search.py     # optional graph search wrapper
└── errors.py                  # Error taxonomy → MCP error results

tests/
├── unit/                      # parsers, dedup, heuristics, sufficiency, errors mapping
├── contract/                  # mcp-tools schema validation, mocked providers (MSAL/Tavily/Exa/SearXNG/Laya)
└── integration/               # stdio e2e, fixture corpus, freshness, failure injection

specs/001-agentic-rag-mcp/fixtures/   # small pdf/docx/xlsx/pptx/mp3 + sample sqlite db
```

**Structure Decision**: Single Python project (pipx-installable CLI). MCP stdio host integration means no web frontend/backend split; Graphify remains an optional extra wired through `search/graphify_search.py` and the `graph.query` tool.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Two semantic layers (LanceDB vectors + Graphify) | Graphify answers entity/relationship queries vectors can't | CocoIndex+LanceDB alone is the default path; Graphify is opt-in and off the fast path |
| Laya app as external runtime dependency | User clarification Q1: actual Laya app is the System 1 decision layer | Embedded-only classifier rejected by user; heuristic fallback keeps the server standalone-capable |

## Phase 0 output

→ [research.md](research.md) — 15 decisions recorded; no NEEDS CLARIFICATION remains.

## Phase 1 outputs

- → [data-model.md](data-model.md) — Document/Chunk/Source/Question/SubTask with lifecycle & validation rules
- → [contracts/mcp-tools.md](contracts/mcp-tools.md) — tool schemas + typed error surface
- → [quickstart.md](quickstart.md) — 6 validation scenarios incl. freshness, failure injection, low-confidence loop exit
