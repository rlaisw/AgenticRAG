# Research: OneDrive Ingestion

**Feature**: specs/006-onedrive-ingestion/spec.md | **Date**: 2026-10-10

All Technical Context unknowns resolved. Zero NEEDS CLARIFICATION.

## D1 — Delta queries for incremental sync (decided in Clarifications)

**Decision**: Use the Graph API's delta endpoint (`/me/drive/root/delta` or `/me/drive/items/{id}/delta`) for the watcher's incremental sync.

**Rationale**: One API call returns only changed items (adds/modifies/deletes) since the last sync. The response includes a `@odata.deltaLink` that is persisted per-source as the sync-state cursor; on the next call, passing this link returns only changes since. Pagination via `@odata.nextLink` in the delta response is handled by following nextLink pages until a deltaLink appears. Microsoft recommends delta queries for file synchronization.

**Alternatives considered**: full listing + diff (rejected: N API calls per cycle, misses pagination, requires manual state management); webhooks/subscriptions (rejected: requires a publicly accessible callback URL — doesn't work for a local server).

## D2 — Recursive folder traversal (initial sync)

**Decision**: For the initial sync (no delta cursor), recursively list the configured folder tree via `GET /me/drive/items/{folder_id}/children` per folder, following child folders recursively. Pagination via `@odata.nextLink` on every listing call.

**Rationale**: The Graph API doesn't support arbitrary-depth expansion in one call (`$expand=children` caps at 3 levels). Recursive per-folder calls are correct for any depth. Each call handles its own pagination.

**Alternatives considered**: `$expand` (rejected: max 3 levels deep, misses deeper folders); `GET /me/drive/root/delta` from scratch (viable: delta from scratch = full listing, but the spec's FR-005 describes the initial listing as a recursive traversal — using delta from scratch for the initial sync is the same thing, just cleaner: it also handles pagination and produces a deltaLink for subsequent syncs).

**Actually**: For simplicity and consistency, use delta queries for BOTH the initial sync AND subsequent syncs. The first delta call (no cursor) returns ALL files; subsequent calls (with cursor) return only changes. This eliminates the need for a separate recursive listing code path. FR-005's "recursive traversal" is satisfied by the delta query's full enumeration.

## D3 — Non-blocking sources_auth flow

**Decision**: The `sources_auth(source_id)` tool returns the device sign-in URL + user code immediately. A background thread runs MSAL's `acquire_token_by_device_flow()` which blocks until the user completes sign-in or the flow times out (~15 minutes). When the thread completes, it saves the token, marks the source healthy, and triggers a sync.

**Rationale**: A blocking tool call would hang the Dify agent's tool execution for minutes — bad UX. Non-blocking lets the agent relay the URL+code immediately, and the user checks back. The background thread uses the same pattern as `laya_runtime.warm_up()` (a daemon thread that doesn't block the server).

**Alternatives considered**: blocking until sign-in (rejected: hangs the agent); polling-based (agent calls sources_auth repeatedly — rejected: unnecessary complexity when MSAL already handles the wait).

## D4 — File download

**Decision**: Each file's `@microsoft.graph.downloadUrl` is a pre-authenticated URL that doesn't require a Bearer token. Download via `httpx.get(download_url, timeout=30, follow_redirects=True)`. The response body is the file content, fed directly into the parser chain.

**Rationale**: The Graph API provides direct download URLs that are valid for a short period — no need to construct authenticated download requests. This is the standard pattern.

**Alternatives considered**: `GET /me/drive/items/{id}/content` (rejected: requires Bearer token and redirects; the downloadUrl is simpler and faster).

## D5 — File size cap

**Decision**: Check `item.size` from the Graph API listing before downloading. Files > 50 MB are skipped with reason `"file too large"`. Configurable via `max_file_size_mb` in the source config.

**Rationale**: The Graph API returns file metadata including size — checking before downloading avoids downloading a 2 GB file into memory.

## D6 — Auth state machine

```
new source → needs_auth
  ↓ (user calls sources_auth, completes browser sign-in)
healthy
  ↓ (token expires, silent refresh fails)
degraded ("sign-in required")
  ↓ (user calls sources_auth again)
healthy
```

The watcher's sync attempt uses `GraphAuth.token()` which tries MSAL silent refresh. If silent refresh fails (no cached token or expired refresh token), it raises `SourceAuthError` → the pipeline marks the source degraded (same as existing local_folder behavior for inaccessible paths).

## D7 — Error handling matrix

| Condition | Behavior | FR |
|---|---|---|
| No valid token at source creation | Source created with status `needs_auth`; response includes sign-in instruction | FR-002 |
| Auth token expired during sync | Source marked degraded: "sign-in required"; other sources continue | FR-010 |
| Graph API returns 429 (rate limit) | Back off; retry on next watcher cycle; source stays healthy | edge case |
| Graph API returns 5xx | Source marked degraded with error; retry next cycle | FR-010 |
| File > 50 MB | Skipped with reason | FR-008 |
| Unsupported file format | Skipped with reason | FR-007 |
| File deleted in OneDrive | Chunks evicted from LanceDB (delta query reports deletion) | FR-009 |
| Empty OneDrive folder | Source healthy with 0 files; no error | edge case |
| Network timeout during download | Individual file skipped with reason; other files continue | FR-010 |

## D8 — Test strategy

**Decision**: Three layers, no live Graph API in CI:
- **Unit** (`test_onedrive.py`): mock `httpx.get` responses for Graph API calls (file listing, delta, download); test pagination (follow `@odata.nextLink`), recursive traversal (child folders), delta parsing (adds/modifies/deletes), size cap, auth error paths, config validation
- **Contract** (`test_onedrive_contract.py`): `sources_add(type: "onedrive")` response shape; `sources_auth` response shape (URL + code format); `sources_list` includes OneDrive sources; frozen tool canary
- **Integration** (`test_onedrive_integration.py`): build_server with mocked Graph API; full sync cycle: add source → mock auth → mock listing → download → parse → embed → verify in LanceDB; delta sync on changed files; eviction on deleted files; auth expiry → degraded

**Rationale**: Same pattern as the web_research tests (mock the external API, test the pipeline end-to-end). No live OneDrive in CI.

## D9 — Config surface

**Decision**: No new `[onedrive]` config section. The OneDrive source is configured per-source via `sources_add`:
```json
{
  "type": "onedrive",
  "config": {
    "client_id": "your-azure-app-id",
    "folder_path": "/Documents",       // optional, default "/" (root)
    "include_subfolders": true,          // optional, default true
    "max_file_size_mb": 50               // optional, default 50
  }
}
```
Token cache path: `~/.config/agentic-rag-mcp/tokens/{source_id}.json` (derived from the source_id, not a config field).

**Rationale**: OneDrive config is per-source, not per-server — the `[onedrive]` section would be wrong. The token cache path is deterministic from the source_id.
