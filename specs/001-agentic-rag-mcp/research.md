# Research: Agentic RAG MCP Server

**Date**: 2026-10-05 | **Feature**: specs/001-agentic-rag-mcp/spec.md

## Decision 1: Language & runtime

- **Decision**: Python 3.12
- **Rationale**: LanceDB, CocoIndex, LangGraph, MCP SDK, and document parsers (unstructured, pypdf, python-docx, openpyxl, python-pptx, faster-whisper) all have first-class Python support. The dev machine already runs Python 3.12/3.14.
- **Alternatives considered**: TypeScript (weaker document-parsing/audio ecosystem); Rust (too slow to iterate for an agentic prototype).

## Decision 2: MCP server framework

- **Decision**: Official `mcp` Python SDK (`FastMCP`) with **stdio transport**.
- **Rationale**: Clarified Q5 — stdio, host-spawned child process. FastMCP gives tool/resource decorators and lifecycle handling out of the box.
- **Alternatives considered**: Streamable HTTP / SSE (rejected for v1 per clarification; may be added later).

## Decision 3: Vector store & incremental pipeline

- **Decision**: **LanceDB** (embedded, file-backed) as the vector DB; **CocoIndex [full]** as the incremental transformation/embedding pipeline feeding it.
- **Rationale**: Explicit user requirement. CocoIndex's change-detection (fingerprint-based incremental indexing) maps directly to FR-004 (add/change/delete without full rebuild). LanceDB is embedded (no server process needed) — fits the single-user stdio deployment.
- **Alternatives considered**: ChromaDB (weaker incremental story), Qdrant/Milvus (require a service process — overkill for single-user), sqlite-vec (fine for small stores but CocoIndex+LanceDB already chosen by user).

## Decision 4: Graphify — keep, optional layer

- **Decision**: Keep **Graphify** as an *optional* semantic-search enhancement over the project/code corpus (and later, document graphs), not the primary retrieval engine.
- **Rationale**: Graphify answers relationship queries ("how is X connected to Y") that pure vector similarity handles poorly. But it is a superset cost: graph build time, cypher-style querying. For general document RAG, vector search (CocoIndex+LanceDB) covers the core. Graphify ships as a separate MCP tool, off the fast path.
- **Alternatives considered**: Graphify as primary search (rejected — slower to build, no clear win for documents); dropping Graphify (rejected — user explicitly listed it).

## Decision 5: System 1 / System 2 routing via Laya

- **Decision**: Integrate with the **Laya desktop app's local MCP surface** (`http://127.0.0.1:8420/mcp/`, bearer token) as the default System 1 classifier; **built-in heuristic fallback** (keyword/length/structure heuristics → default deliberative) when Laya is unreachable.
- **Rationale**: User clarified Q1=A — run the actual Laya app locally as the decision layer. A fallback is mandatory to keep the server usable without Laya (acceptance: degradation is reported, answers still produced).
- **Alternatives considered**: Embedded-only classifier (rejected by user); always-fail without Laya (unusable).

## Decision 6: Deliberative loop engine

- **Decision**: **LangGraph** for the System 2 reflection/planning loop (plan → route → retrieve → sufficiency check → loop/answer), ReAct-style.
- **Rationale**: Explicit user requirement; LangGraph provides durable graph state machines with checkpointing, well-suited to bounded-iteration loops with a configurable budget (FR-014/FR-017).
- **Alternatives considered**: Hand-rolled loop (fragile); LangChain Agents without graph (less control over sufficiency-check branching).

## Decision 7: Document & audio parsing

- **Decision**: `pypdf`/`pdfplumber` (PDF), `python-docx` (Word), `openpyxl` (Excel), `python-pptx` (PowerPoint), `faster-whisper` (audio transcription, local).
- **Rationale**: All local, no hosted APIs — matches Q3 (local embeddings default) and single-user privacy. faster-whisper runs on CPU with small models.
- **Alternatives considered**: unstructured.io (heavier deps); cloud transcription (violates local default).

## Decision 8: Embeddings

- **Decision**: Local embedding model via `sentence-transformers` (default `all-MiniLM-L6-v2`, matching the machine's existing CocoIndex global config), swapped easily via config.
- **Rationale**: Q3 clarified local embeddings; reusing the already-downloaded model avoids cold-start downloads. Config allows ONNX/GGUF alternatives later.
- **Alternatives considered**: Hosted OpenAI/Cohere embeddings (rejected for default; allowed as opt-in config).

## Decision 9: OneDrive / SharePoint Online auth

- **Decision**: **Delegated per-user OAuth 2.0** with MSAL (`msal` Python lib), device-code or interactive-browser flow, token cache on local disk.
- **Rationale**: Q4 clarified per-user delegated auth; app-only daemon access out of scope. MSAL is the Microsoft-supported library; token cache makes re-auth rare.
- **Alternatives considered**: App-only client credentials (rejected per clarification); raw OAuth by hand (needless risk).

## Decision 10: Web search providers

- **Decision**: Pluggable provider interface with adapters for **Tavily**, **Exa**, and self-hosted **SearXNG**; config selects one or more with fallback order.
- **Rationale**: FR-011 requires at least one pluggable provider; adapter pattern keeps FR-004-style degradation behavior (SC-005) simple.
- **Alternatives considered**: Single hardwired provider (rejected — user listed three).

## Decision 11: SQLite data source

- **Decision**: Read-only SQLite source connector: user maps tables/columns → document text template; changes detected via content hash of rendered rows (+ optional file mtime fast-path).
- **Rationale**: FR-002. Read-only avoids accidental mutation of user databases; hash-based change detection plugs into the same incremental pipeline (CocoIndex custom source or a small watcher feeding the same embedding step).
- **Alternatives considered**: Full SQL query tool against arbitrary DBs (deferred to the deliberative tool-routing as read-only SQL tool; direct live SQL answering is a v1.1 consideration).

## Decision 12: Deduplication

- **Decision**: Content-hash (SHA-256 of normalized extracted text) as the dedup key across sources; store `origin[]` list of all source locations on the canonical document.
- **Rationale**: FR-006. Hash catch is cheap; cross-source identity is exact-content-based (not filename-based) to survive renames/moves.
- **Alternatives considered**: Near-dedup (MinHash/embedding similarity) — deferred; v1 does exact-duplicate collapsing only.

## Decision 13: Testing strategy

- **Decision**: `pytest` with three layers:
  1. **Unit**: parsers, chunking, dedup, sufficiency heuristics, routing fallback (incl. Laya-unreachable path) — no network, no GPU.
  2. **Contract**: MCP tool schema tests (`contracts/mcp-tools.json`), provider-adapter fakes (Tavily/Exa/SearXNG/MSAL mocked), CocoIndex flow on a fixture corpus.
  3. **Integration**: end-to-end stdio session with `mcp` test client; fixture corpus (small PDF/DOCX/XLSX/PPTX/MP3), real LanceDB in a tmp dir, real local embedding model; error paths asserted (corrupt file, expired token, provider down, loop-budget exhausted).
- **Rationale**: The user explicitly requested "create test cases and add error handling"; every failure edge case in the spec maps to at least one test.
- **Alternatives considered**: unittest (pytest ecosystem is richer for async); e2e only (too slow to iterate).

## Decision 14: Error handling & observability

- **Decision**: Typed error taxonomy (`IngestionError`, `SourceAuthError`, `ProviderError`, `SufficiencyExhausted`, `DecisionLayerUnavailable`) mapped to MCP error results; structured JSON logs per request with correlation IDs; per-source health status (`healthy|degraded|down`) surfaced via a status tool.
- **Rationale**: SC-005 requires degraded sources to be clearly reported; FR-017 requires low-confidence flagging. MCP clients must receive machine-distinguishable errors, not stack traces.
- **Alternatives considered**: Exceptions bubbled raw to clients (rejected — leaks internals, breaks testability).

## Decision 15: Dependency delivery

- **Decision**: `pyproject.toml` with `pipx`-installable CLI `agentic-rag-mcp` entry point; heavy deps (whisper, torch-free via faster-whisper/CTranslate2, sentence-transformers) pinned with platform notes; optional extras `[graphify]`, `[audio]`.
- **Rationale**: Single-user stdio deployment; pipx isolation matches how `ccc`/`graphify` are already installed on this machine.
