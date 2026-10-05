# MCP Tool Contracts: Agentic RAG MCP Server

Transport: **stdio** (host-spawned child process). Protocol: MCP (JSON-RPC over stdio).

## Tools

### 1. `ask` — Q&A with agentic retrieval

**Input**
```json
{
  "question": "string (required)",
  "collections": ["string"] ,
  "mode": "auto | fast | deep",
  "max_iterations": "int (optional, default from config)"
}
```

**Output (success)**
```json
{
  "answer": "string",
  "confidence": "normal | low",
  "classification": "fast | deliberative",
  "citations": [{ "kind": "document | web", "ref": "document_id | url", "title": "string" }],
  "trace": [{ "tool": "string", "query": "string", "hits": "int" }],
  "degraded_sources": ["string"]
}
```

**Errors**: `SufficiencyExhausted` (returned as `confidence: low`, not an RPC error), `DecisionLayerUnavailable` (downgraded to fallback path, noted in `trace`).

### 2. `sources.list` / `sources.add` / `sources.remove`

- `sources.add` input: `{ "type": "local_folder|sqlite|onedrive|sharepoint", "config": {...} }` → returns `{ "source_id", "status" }`. Triggers first sync.
- `sources.list` output: `[{ "id", "type", "health", "health_reason", "last_sync_at", "doc_count" }]`
- Auth failure ⇒ `health: degraded`, `health_reason: "auth_expired"` (US-edge-case), never throws to the caller.

### 3. `sources.sync` (optional manual trigger)

Input: `{ "source_id" }` → output: `{ "added": int, "updated": int, "deleted": int, "skipped": [{ "locator", "reason" }] }`

### 4. `search` — direct retrieval (no synthesis)

Input: `{ "query": "string", "collections": [...], "limit": int }`
Output: `[{ "chunk_id", "document_id", "title", "snippet", "score", "origin" }]`

### 5. `graph.query` — Graphify layer (optional, feature-flagged)

Input: `{ "query": "string" }` → Output: `{ "nodes": [...], "edges": [...], "answer": "string" }`
Disabled ⇒ returns structured error `FeatureDisabled`.

### 6. `status` — server health

Output: `{ "version": "string", "decision_layer": "laya|fallback|down", "sources": [...health...], "index": { "documents": int, "chunks": int, "last_sync_at": "datetime" } }`

## Error surface

All tool-level failures return MCP error results with a machine-readable `code` field: `NotFound`, `AuthRequired`, `ProviderUnavailable`, `ParseFailed`, `BudgetExhausted`, `FeatureDisabled`. Stack traces are never returned over the wire (logged server-side only).
