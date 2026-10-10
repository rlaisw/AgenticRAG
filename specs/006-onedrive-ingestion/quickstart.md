# Quickstart: OneDrive Ingestion Validation

**Feature**: specs/006-onedrive-ingestion/spec.md

## Prerequisites

- Azure AD app registration with `Files.Read` delegated permission and a `client_id`
- Sidecar running (aligned port 28080)
- Files in OneDrive (at least 1 PDF or DOCX for the search test)

## S1 — Add a OneDrive source (FR-001)

```bash
curl -s -m 30 http://localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"sources_add","arguments":{"type":"onedrive","config":{"client_id":"YOUR_CLIENT_ID"}}}}'
```

**Expected (first time)**: `{"source_id": "...", "status": "needs_auth"}` — no token yet.
**Expected (returning)**: `{"source_id": "...", "status": "ok", "sync": {...}}` — token cached, files synced.

## S2 — Complete device sign-in (FR-003)

```bash
curl -s -m 30 http://localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"sources_auth","arguments":{"source_id":"YOUR_SOURCE_ID"}}}'
```

**Expected**: `{"status": "sign_in_required", "sign_in_url": "https://microsoft.com/devicelogin", "user_code": "ABC123"}`

Open the URL in a browser, enter the code, sign in with your Microsoft account. Then check:

```bash
curl -s http://localhost:28080/mcp ... {"name":"status","arguments":{}}
```

**Expected**: source shows `health: "healthy"`.

## S3 — Verify files are searchable (SC-001)

```bash
curl -s -m 60 http://localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ask","arguments":{"question":"What does YOUR_DOCUMENT say about ..."}}}'
```

**Expected**: answer with citations referencing your OneDrive file.

## S4 — Auto-update (SC-002/003)

1. Upload a new file to OneDrive
2. Wait ≤5 minutes (one watcher cycle)
3. Ask a question about the new file → it's searchable

4. Edit an existing file in OneDrive
5. Wait ≤5 minutes
6. Ask the same question → the answer reflects the NEW content (old chunks evicted)

## S5 — Auth expiry (SC-004)

1. Let the token expire (or simulate by deleting the token cache file)
2. Wait for the watcher → source shows `degraded: "sign-in required"`
3. Other sources (local_folder, sqlite) still healthy and syncing
4. Call `sources_auth` again → re-auth → source returns to healthy

## S6 — Contract freeze (SC-005)

```bash
.venv/bin/python -m pytest tests/ -q
```

**Expected**: all existing 152 tests + new OneDrive tests green; `web_search`, `web_research`, `specialty_search` canaries unchanged.

## Notes

- Full schema: [contracts/onedrive-source.md](contracts/onedrive-source.md)
- Entities and sync lifecycle: [data-model.md](data-model.md)
- After implementation: refresh Dify's MCP tool cache (13→14 tools with `sources_auth`)
- Azure AD setup: Portal → Azure Active Directory → App registrations → New → add `Files.Read` delegated permission → copy the Application (client) ID
