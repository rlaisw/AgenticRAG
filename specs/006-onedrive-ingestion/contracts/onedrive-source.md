# Contract: OneDrive Source + `sources_auth` MCP Tools

**Feature**: specs/006-onedrive-ingestion/spec.md | FR-001..FR-014

New, additive MCP tool + source type. All existing tool response shapes are UNCHANGED (Constitution I / SC-005).

## `sources_add(type: "onedrive")`

### Request
```json
{
  "type": "onedrive",
  "config": {
    "client_id": "your-azure-app-id",
    "folder_path": "/Documents",
    "include_subfolders": true,
    "max_file_size_mb": 50
  }
}
```

### Response (existing token, immediate sync)
```json
{
  "source_id": "a1b2c3d4e5f6",
  "status": "ok",
  "sync": {"added": 12, "updated": 0, "deleted": 0, "skipped": [{"locator": "img.png", "reason": "unsupported format"}]}
}
```

### Response (no token, needs sign-in)
```json
{
  "source_id": "a1b2c3d4e5f6",
  "status": "needs_auth",
  "sign_in_url": "https://microsoft.com/devicelogin",
  "user_code": null
}
```

## `sources_auth(source_id)` (new tool)

### Request
```json
{"source_id": "a1b2c3d4e5f6"}
```

### Response (sign-in needed — starts device flow)
```json
{
  "status": "sign_in_required",
  "sign_in_url": "https://microsoft.com/devicelogin",
  "user_code": "ABC123",
  "message": "Visit the URL, enter the code, and sign in with your Microsoft account. The connection completes automatically."
}
```

### Response (already authenticated)
```json
{"status": "already_authenticated", "message": "This source has a valid token."}
```

### Response (sign-in completed — checked after user returns)
```json
{"status": "authenticated", "message": "Sign-in successful. Syncing now."}
```

## `sources_list` (unchanged shape, OneDrive sources included)

```json
[
  {"id": "a1b2c3d4e5f6", "type": "onedrive", "health": "healthy"},
  {"id": "5fe9da997311", "type": "local_folder", "health": "healthy"}
]
```

## Invariants

1. **Contract freeze** (FR-012 / SC-005): the 152-test suite passes unchanged; all existing tool response shapes are byte-identical.
2. **Delta sync** (FR-009): the watcher uses Graph API delta queries — one call for all changes, `@odata.deltaLink` persisted per-source, pagination via `@odata.nextLink`.
3. **Pagination** (FR-014): ALL Graph API listing calls follow `@odata.nextLink` — no silently dropped files.
4. **Honest errors** (FR-013): unsupported formats, oversized files, auth failures, API errors all produce explicit reasons.
5. **Auth isolation** (FR-010): a OneDrive auth failure marks that source degraded and never blocks other sources.
6. **Eviction** (FR-009 / SC-003): deleted OneDrive files have their chunks evicted from LanceDB — same as local_folder.
7. **Non-blocking auth** (D3): `sources_auth` returns the URL+code immediately; completion detected on the next `status`/`sources_list` call or watcher cycle.
