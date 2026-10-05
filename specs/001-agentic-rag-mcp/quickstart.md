# Quickstart: Agentic RAG MCP Server

Validation scenarios proving the feature end-to-end. Prerequisites and expected outcomes only — no implementation code here.

## Prerequisites

1. Python 3.12+, `pipx` installed.
2. Optional (for Laya decision layer): Laya desktop app running locally with MCP enabled at `http://127.0.0.1:8420/mcp/` and its bearer token.
3. Optional (for web search): a Tavily or Exa API key, or a local SearXNG instance URL.
4. Optional (for OneDrive/SharePoint): Microsoft app registration with delegated `Files.Read`/`Sites.Read.All` scopes.

## Setup

```bash
pipx install -e .
agentic-rag-mcp --init            # writes ~/.config/agentic-rag-mcp/config.toml
```

## Scenario 1 — Local folder → fast answer (P1)

1. Create `~/demo-docs/` with a PDF and a DOCX containing distinct facts.
2. `mcp-client call sources.add '{"type":"local_folder","config":{"path":"~/demo-docs"}}'`
3. Wait for `sources.sync` to report `added: 2`.
4. `ask({"question": "<fact from the PDF>"})` → expect: answer contains the fact; `citations` includes the PDF; `classification` is `fast` (or `deliberative` with `fallback` when Laya is not running).

**Pass criteria**: sourced answer in < 10 s; citation points at the right file.

## Scenario 2 — Incremental update (P1)

1. Edit the DOCX (add a new fact).
2. Within the freshness window, `ask` about the new fact → returned with the DOCX citation.
3. Delete the PDF.
4. `ask` the PDF-only question again → answer reports no relevant information; PDF absent from `search` results.

## Scenario 3 — Multi-source deep research (P2)

1. Add a SQLite source with a table of records and keep the local docs.
2. `ask` a question requiring both sources (e.g., "Summarize <doc topic> and compare with the numbers in <table>"), `mode: "deep"`.
3. Expect `trace` to show ≥ 2 tools (`vector_search`, `sql_query`), per-sub-task citations, `confidence: normal`.

## Scenario 4 — Web search fallback (P3)

1. Configure a SearXNG URL (or Tavily/Exa key).
2. Ask about a recent public event not present locally → answer cites `kind: "web"` URLs.
3. Poison the provider config → repeat → expect `degraded_sources` to name the web provider and the answer (if any) to come from local sources only.

## Scenario 5 — Error handling assertions

- Drop a corrupt PDF into the folder → `sources.sync` lists it under `skipped` with reason; other docs still indexed.
- Expire the OneDrive token → `sources.list` shows that source `degraded/auth_expired`; `ask` still works on healthy sources.
- Run with Laya stopped → `status` shows `decision_layer: fallback`; answers still returned with the degradation noted.
- Ask an unanswerable question with `mode: "deep"` → responses stop at the iteration budget with `confidence: low` and no fabricated citations.

## Scenario 6 — MCP client wiring (stdio)

Add to the host config and verify the tools register:

```json
{ "mcpServers": { "agentic-rag": { "command": "agentic-rag-mcp" } } }
```

Expect `ask`, `search`, `sources.*`, `status` (and `graph.query` when enabled) to appear in the host's tool list.
