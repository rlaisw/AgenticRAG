# Feature Specification: OneDrive Ingestion — Full Pipeline with Auto-Update

**Feature Branch**: `006-onedrive-ingestion`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "I have some files on Microsoft OneDrive (Office documents and PDF files) and I want to embed the files to my local LanceDB database, so I can use AgenticRAG to answer my question. Also it can auto-update the embedding process."

**Existing contracts (Constitution I)**: All existing tool response shapes are frozen. This feature adds OneDrive as a new source type within the existing `sources_add` tool — no existing tool changes.

## Clarifications

### Session 2026-10-10

- Q: How should the incremental sync detect changes in OneDrive — by comparing full file listings each cycle, or by using the Graph API's delta endpoint? → A: **Delta queries** (user decision, 2026-10-10) — the Graph API's delta endpoint is Microsoft's recommended file-sync mechanism: one API call returns only changed items (adds, modifications, AND deletions) since the last sync, handles pagination natively via `@odata.nextLink`, and eliminates the need for manual state diffing. The spec-002 eviction fix applies to deleted items exactly as it does for local folders.

**Existing foundation (spec 001, already implemented)**:
- `sources/graph_auth.py` — MSAL per-user delegated auth (device code flow, token cache, silent refresh)
- `sources/onedrive.py` — `OneDriveSource` with Graph API file listing (top-level)
- `sources/sharepoint.py` — `SharePointSource` (site-based listing)
- The ingestion pipeline (`sync_local_folder`, `sync_sqlite`), parsers (PDF/DOCX/XLSX/PPTX/audio), dedup, chunking, embedding, and the 5-minute watcher — all fully working for local_folder and sqlite sources

**What's missing (the gap this spec covers)**:
- The ingestion pipeline has no `sync_onedrive` method — OneDrive files are listed but never downloaded, parsed, or embedded
- The `sources_add` tool doesn't accept `type: "onedrive"`
- The watcher doesn't handle OneDrive sources
- No device sign-in flow exposed through MCP tools
- File listing is top-level only (no recursive folder traversal)
- No file download through the Graph API download URL

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Add and Authenticate a OneDrive Source (Priority: P1)

A user has Office documents and PDFs in their OneDrive. They call `sources_add` with `type: "onedrive"`. The system checks for existing authentication — if no valid token, it initiates a device code flow: the user sees a URL and a code on their terminal, visits the URL, enters the code, and signs in with their Microsoft account. After sign-in, the system lists the files in their OneDrive, downloads each supported file (PDF, DOCX, XLSX, PPTX), parses it through the same ingestion pipeline as local files, and embeds the content into LanceDB. The source appears in `sources_list` as healthy.

**Why this priority**: This is the core value — the user's cloud files become searchable in their local knowledge base. Without this step, nothing else matters.

**Independent Test**: Register a OneDrive source with valid credentials → `sources_list` shows it healthy → ask a question about a known file's content → the answer cites it. Register with expired credentials → the source is marked degraded with a re-auth needed message.

**Acceptance Scenarios**:

1. **Given** the user has an Azure AD app with `Files.Read` permission, **When** they call `sources_add(type: "onedrive", config: {client_id})`, **Then** the system returns a device sign-in URL and code, and after the user completes sign-in, files are listed and ingestion begins.
2. **Given** a valid token exists in the cache, **When** a OneDrive source is added, **Then** no re-auth is needed — files are ingested immediately (silent token refresh).
3. **Given** the user's OneDrive contains 10 files (5 PDFs, 3 DOCX, 1 XLSX, 1 PNG), **When** the source syncs, **Then** the 9 supported files are ingested and the PNG is skipped with a reason (unsupported format — same behavior as local_folder).
4. **Given** the token has expired and MSAL cannot silently refresh, **When** the watcher attempts to sync, **Then** the source is marked degraded with "sign-in required" and other sources continue syncing (Constitution IV — one source's failure never blocks others).
5. **Given** the user has nested folders in OneDrive, **When** files are listed, **Then** files from all nested subfolders are found (recursive traversal).

---

### User Story 2 — Auto-Update from OneDrive (Priority: P1)

The 5-minute watcher detects changes in the user's OneDrive: new files are downloaded and embedded; edited files have their content re-embedded (the eviction fix from spec 002 ensures old chunks are replaced, not duplicated); deleted files stop appearing in search results. The user does nothing — their knowledge base stays current automatically.

**Why this priority**: The user explicitly requested auto-update — "it can auto-update the embedding process." This is the ongoing value after the initial setup.

**Independent Test**: Add a file to OneDrive → wait one watcher cycle (≤5 minutes) → `search` finds it. Edit a file → wait one cycle → the answer reflects the new content and the old content is gone.

**Acceptance Scenarios**:

1. **Given** a OneDrive source is healthy, **When** a new file is uploaded to OneDrive, **Then** within one watcher cycle the file is ingested and searchable.
2. **Given** an existing file is edited in OneDrive, **When** the watcher syncs, **Then** the old chunks are evicted and new content is embedded (the spec-002 eviction fix applies to OneDrive sources identically).
3. **Given** a file is deleted from OneDrive, **When** the watcher syncs, **Then** the file's content stops appearing in search results.
4. **Given** the OneDrive source has 100 files and 2 have changed, **When** the watcher syncs, **Then** only the 2 changed files are re-downloaded and re-embedded (incremental sync, not full re-ingestion).

---

### User Story 3 — Credential Lifecycle Management (Priority: P2)

The user needs to manage their Microsoft authentication: initiate sign-in, refresh tokens silently when possible, and re-authenticate when tokens expire. The system provides an explicit `sources_auth` tool that returns the device sign-in flow when needed and a status that tells the user which sources need re-authentication.

**Why this priority**: Credentials are a prerequisite for US1/US2 but are managed independently — once set up, they usually "just work" with silent refresh. The explicit tool is needed for initial setup and rare re-auth.

**Independent Test**: Call `sources_auth(source_id)` on a new source → get the sign-in URL/code → complete sign-in → source becomes healthy. Call on a healthy source → get "already authenticated."

**Acceptance Scenarios**:

1. **Given** a newly added OneDrive source has no token, **When** `sources_auth(source_id)` is called, **Then** the response contains a device sign-in URL and user code.
2. **Given** a source already has a valid token, **When** `sources_auth(source_id)` is called, **Then** the response says "already authenticated" — no re-auth flow started.
3. **Given** a token expired and silent refresh failed, **When** the watcher runs, **Then** the source health shows "degraded: sign-in required" and `sources_auth` returns the re-auth flow.

---

### Edge Cases

- What if the user's OneDrive is empty? (Source is healthy with 0 files — no error.)
- What if a file is too large to download (>50 MB)? (Skipped with a reason: "file too large for auto-ingestion.")
- What if OneDrive returns a rate limit (HTTP 429)? (Back off and retry on the next watcher cycle; source stays healthy.)
- What if the Graph API is down? (Source marked degraded with the error; other sources continue; next watcher cycle retries.)
- What if the user has multiple OneDrive sources? (Each has its own token cache and config — they are independent.)
- What if a file is shared with the user but owned by someone else? (Files in `/me/drive` only — shared-with-me files are out of scope.)
- What if the same file exists in both a local folder and OneDrive? (Content-hash dedup handles it — the file is ingested once with both origins, per spec 001 edge case.)

## Requirements *(mandatory)*

### Functional Requirements

**Source registration and authentication**

- **FR-001**: The `sources_add` tool MUST accept `type: "onedrive"` with config `{client_id, folder_path (optional, default root), include_subfolders (optional, default true)}`, creating the source and checking for an existing valid token.
- **FR-002**: If no valid token exists, the source is created with status `needs_auth` and the response includes a device sign-in instruction; the user calls `sources_auth` to complete the flow.
- **FR-003**: A new `sources_auth(source_id)` tool MUST initiate the MSAL device code flow and return the sign-in URL and user code; on completion, the source transitions to healthy.
- **FR-004**: Token cache MUST be per-source (each OneDrive source has its own MSAL token cache file) and MUST use MSAL's silent refresh when possible.

**File discovery and ingestion**

- **FR-005**: The ingestion pipeline MUST list files from the configured OneDrive folder (and subfolders if `include_subfolders` is true) via the Graph API, using recursive traversal for nested folders.
- **FR-006**: Each supported file (PDF, DOCX, XLSX, PPTX — same formats as local_folder) MUST be downloaded via its Graph API download URL, parsed through the existing parser chain, deduplicated by content-hash, chunked, and embedded into LanceDB — identical to local_folder ingestion.
- **FR-007**: Unsupported file formats (images, videos, executables) MUST be skipped with a reason in the sync stats — identical to the local_folder behavior.
- **FR-008**: Files larger than a configurable bound (default 50 MB) MUST be skipped with a reason (not downloaded).

**Auto-update**

- **FR-009**: The 5-minute watcher MUST sync OneDrive sources using the Graph API's **delta endpoint** (decided in Clarifications): one API call returns only changed items (adds/modifies/deletes) since the last sync; the delta-link cursor is persisted per-source as sync state; new/changed files are downloaded and ingested; deleted files have their chunks evicted (spec 002 eviction fix); pagination via `@odata.nextLink` is handled transparently.
- **FR-010**: A OneDrive sync failure (auth error, network error, rate limit) MUST mark the source degraded and MUST NOT block other sources from syncing — the same isolation as local_folder and sqlite sources.
- **FR-011**: The `sources_sync` tool MUST work for OneDrive sources (manual sync trigger with per-source stats).
- **FR-014**: ALL Graph API listing calls MUST handle pagination via `@odata.nextLink` — the current `OneDriveSource.files()` returns only the first page (~200 items); with more files, subsequent pages are silently missed (correctness requirement, found in double-clarify).

**Constitution compliance**

- **FR-012**: All existing tool response shapes MUST remain unchanged (Constitution I / SC-004); the new source type and `sources_auth` tool are purely additive.
- **FR-013**: Every error/fallback MUST be honest (Constitution IV): unsupported files, oversized files, auth failures, and API errors all produce explicit reasons — never silent skips, never fabricated content.

### Key Entities

- **OneDriveSourceConfig**: the source configuration — `client_id` (Azure AD app), `folder_path` (default `/` root), `include_subfolders` (default true), `max_file_size_mb` (default 50).
- **GraphFileListing**: the result of listing OneDrive files — per file: `locator` (Graph item ID), `title`, `download_url`, `last_modified` (for incremental change detection), `size` (for the size bound).
- **OneDriveSyncState**: the watcher's incremental state — the **delta-link cursor** from the Graph API (a URL that returns only changes since the last call); persisted per-source, reset on full re-auth.
- **TokenCachePath**: per-source MSAL token cache location — `~/.config/agentic-rag-mcp/tokens/{source_id}.json`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A OneDrive source with 5 supported files (PDF/DOCX/XLSX/PPTX) ingests all 5 into LanceDB within the first sync; each is searchable via `ask` with citations.
- **SC-002**: A new file uploaded to OneDrive becomes searchable within one watcher cycle (≤5 minutes).
- **SC-003**: An edited file's old chunks are evicted and new content replaces them — verified by asking the same question before and after the edit, with the answer reflecting the new content only.
- **SC-004**: An expired token marks the source `degraded` with a re-auth message; other sources continue syncing; completing `sources_auth` restores the source to healthy.
- **SC-005**: The 152-test suite passes unchanged (Constitution I); new OneDrive tests are additive.
- **SC-006**: Unsupported and oversized files produce honest skip reasons in sync stats (never silent, never fabricated).

## Assumptions

- The user has (or will create) an Azure AD app registration with `Files.Read` delegated permission and a client_id — this is a user prerequisite, not something the system provides.
- MSAL per-user delegated auth is already implemented in `sources/graph_auth.py` (device code flow, silent refresh) — this feature wires it into the source pipeline, it does not rewrite the auth layer.
- The Graph API's `@microsoft.graph.downloadUrl` provides a direct download link per file — already used by the existing `OneDriveSource.files()` listing.
- Incremental change detection uses Graph API item metadata (last modified timestamp + item ID), not content hashing on the remote side (the existing content-hash dedup still applies after download).
- Out of scope: SharePoint (separate source type, future feature if requested); shared-with-me files (only `/me/drive` is scanned); file upload/write-back to OneDrive; file preview (Graph API thumbnails).
- The 5-minute watcher interval and the eviction fix (spec 002) apply unchanged — OneDrive sources are first-class citizens in the same incremental pipeline.
