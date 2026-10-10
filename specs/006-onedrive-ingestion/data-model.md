# Data Model: OneDrive Ingestion

**Feature**: specs/006-onedrive-ingestion/spec.md

## Entities

### OneDriveSourceConfig
Per-source configuration, stored in the state DB's source record.

| Field | Type | Default | Validation | Notes |
|---|---|---|---|---|
| client_id | string | required | non-empty | Azure AD app registration ID |
| folder_path | string | "/" | non-empty | Graph API path relative to the drive root |
| include_subfolders | bool | true | — | Whether to recurse into child folders |
| max_file_size_mb | int | 50 | > 0 | Files larger are skipped with a reason |

### GraphFileItem
One file/folder item from the Graph API listing.

| Field | Type | Notes |
|---|---|---|
| id | string | Graph item ID (the source locator) |
| name | string | File name (the title) |
| size | int | Bytes — checked against max_file_size_mb before download |
| downloadUrl | string \| null | Pre-authenticated direct download URL (null for folders) |
| lastModifiedDateTime | string | ISO 8601 timestamp (observability; delta queries don't need it) |
| file | dict \| null | MIME type info (null for folders) |
| folder | dict \| null | Folder marker (null for files) |
| deleted | dict \| null | Present only in delta responses — item was deleted |

### OneDriveSyncState
Per-source incremental sync state, stored in the state DB's source `sync_state`.

| Field | Type | Notes |
|---|---|---|
| delta_link | string | The `@odata.deltaLink` URL from the last delta call — passed back on the next sync to get only changes |
| last_sync_at | string | ISO timestamp (observability) |

State transitions:
```
no delta_link (initial sync) → delta call without cursor → returns ALL items + delta_link → persist
has delta_link (subsequent) → delta call with cursor → returns CHANGED items + new delta_link → persist
re-auth after expiry → reset delta_link → full re-sync on next cycle
```

### TokenCache
Per-source MSAL token cache.

| Field | Type | Notes |
|---|---|---|
| path | Path | `~/.config/agentic-rag-mcp/tokens/{source_id}.json` |
| content | str | MSAL SerializableTokenCache serialized JSON |
| contains_refresh_token | bool | True after device sign-in; enables silent refresh |

## Request lifecycle

```
sources_add(type: "onedrive", config) →
  create source record → check token cache →
  has token? → healthy → trigger initial sync
  no token? → needs_auth → response: {source_id, status: "needs_auth", sign_in_url: null}

sources_auth(source_id) →
  initiate MSAL device flow →
  return {sign_in_url, user_code} immediately (non-blocking) →
  background thread: acquire_token_by_device_flow() →
  user completes browser sign-in →
  thread saves token → marks source healthy → triggers sync

sync_onedrive(source_id, config, auth) →
  get token via auth.token() (silent refresh if possible) →
  has delta_link? → GET delta_link (changes only)
  no delta_link? → GET /me/drive/root/delta (full initial) →
  follow @odata.nextLink pages →
  for each item:
    item.deleted? → evict chunks from LanceDB (spec 002)
    item.folder AND include_subfolders? → recurse into children
    item.size > max_file_size_mb? → skip with reason
    supported format? → download via downloadUrl → parse → dedup → chunk → embed → LanceDB
    unsupported? → skip with reason
  persist new delta_link →
  update source health: healthy → return stats
```

## File format filtering (same as local_folder)

| Extension | Status |
|---|---|
| .pdf, .docx, .xlsx, .pptx | ✅ parsed and embedded |
| .mp3, .wav, .m4a | skipped (audio requires `[audio]` extra; sidecar has it disabled) |
| .txt, .md, .csv | skipped (not in the parser chain) |
| .png, .jpg, .exe, .zip | skipped with reason "unsupported format" |
| no extension / folder | folder → recurse; file with no extension → skipped |
