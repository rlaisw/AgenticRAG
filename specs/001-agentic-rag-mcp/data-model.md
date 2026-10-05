# Data Model: Agentic RAG MCP Server

**Feature**: specs/001-agentic-rag-mcp/spec.md

## Entities

### Document
Canonical ingested item (deduplicated by content).

| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | internal id |
| content_hash | string (sha256) | dedup key across all sources |
| title | string | from metadata or filename |
| extracted_text | text | parsed/transcribed content |
| media_type | enum | `pdf|docx|xlsx|pptx|audio|sqlite_record|web` |
| origins | list[OriginRef] | every source location holding identical content |
| ingested_at | datetime | first seen |
| updated_at | datetime | last content change |
| status | enum | `ok|failed|skipped` + `status_reason` (corrupt/encrypted/no-speech/…) |

### OriginRef
One physical location of a Document.

| Field | Type | Notes |
|---|---|---|
| source_id | string | FK → Source |
| locator | string | file path / drive item id / "table:rowpk" / URL |
| last_seen_at | datetime | for deletion detection |

### Chunk
Embedded segment of a Document (row in LanceDB).

| Field | Type | Notes |
|---|---|---|
| id | string | `${document_id}:${chunk_index}` |
| document_id | string | FK |
| text | text | |
| embedding | vector(384) | local model default |
| collection | string | routing label (maps to Source/domain) |

**Lifecycle**: on Document content change → old Chunks invalidated (delete), new Chunks inserted. On Document deletion → all Chunks + OriginRefs removed. FR-004.

### Source (Connector config + health)

| Field | Type | Notes |
|---|---|---|
| id | string | |
| type | enum | `local_folder|sqlite|onedrive|sharepoint|web_tavily|web_exa|web_searxng` |
| config | json | path / db path + table map / drive+site / endpoint+key |
| credentials_ref | string | pointer to token cache / keyring entry (never stored inline) |
| sync_state | json | high-water marks (mtime, delta-token, row hashes) |
| health | enum | `healthy|degraded|down` + `health_reason` |
| last_sync_at | datetime | |

### Question session (deliberative trace)

| Field | Type | Notes |
|---|---|---|
| id | string | |
| question | text | |
| classification | enum | `fast|deliberative` (+ `classifier: laya|fallback`) |
| plan | list[SubTask] | deliberative only |
| iterations | int | bounded by budget |
| sufficiency | enum | `satisfied|exhausted` |
| answer | text | with `confidence: normal|low` |
| citations | list[CitationRef] | document_id + chunk_id / web URL |

### SubTask
| Field | Type | Notes |
|---|---|---|
| id, tool | `vector_search|sql_query|web_search|onedrive|sharepoint|graphify` | |
| input, result_refs | — | provenance per sub-task (FR-016) |

## Validation rules
- `Document.content_hash` unique across corpus (FR-006).
- Source deletion ⇒ Document dropped only when its last OriginRef is removed.
- `Question.iterations` ≤ configured budget (FR-014); on exhaustion `confidence=low` (FR-017).
- Web answers must set `CitationRef.kind=web` with URL (US-4).
