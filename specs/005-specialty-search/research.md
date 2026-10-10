# Research: Specialty Web Search

**Feature**: specs/005-specialty-search/spec.md | **Date**: 2026-10-10

All Technical Context unknowns resolved. Zero NEEDS CLARIFICATION.

## D1 — Profile file format and location

**Decision**: JSON file at `~/.config/agentic-rag-mcp/specialty_profiles.json` (user-managed, not committed). Path overridable via `config.toml [web.specialty] file = "..."`. Format: `{name: {"sites": [str], "description": str}}` — name is the JSON key (case-insensitive lookup).

**Rationale**: User explicitly chose JSON for easy management; the file sits alongside `config.toml` in the already-mounted config volume (host edits visible in the container instantly).

**Alternatives considered**: config.toml tables (rejected — user prefers JSON); YAML (rejected — user said JSON); in-memory config (rejected — user wants to edit the file directly).

## D2 — Hot-reload mechanism

**Decision**: Read the JSON file on EVERY `specialty_search` and `specialty_profiles` call. No in-memory cache, no file-watching, no restart needed.

**Rationale**: File reads are ~microseconds; a 20-profile file is <5 KB; caching adds staleness bugs for zero measurable performance gain (ponytail: cache only if profiling shows a problem). The config volume bind-mount means host edits are immediately visible inside the container.

**Alternatives considered**: watch-file + in-memory cache (rejected — complexity for no benefit); restart-required (rejected — user explicitly wants hot-reload).

## D3 — Query construction (site: operator)

**Decision**: For a profile with sites `["learn.microsoft.com", "techcommunity.microsoft.com"]` and query `"DKIM Exchange Online"`, construct:

```
site:learn.microsoft.com OR site:techcommunity.microsoft.com DKIM Exchange Online
```

Multiple sites joined with ` OR `. The full string is passed to the existing `search_all(providers, query, limit)` — zero adapter changes.

**Rationale**: SearXNG forwards the `site:` operator to Google/Bing/DDG which enforce it as a hard filter. Tavily and Exa also honor `site:` in query strings. The chain is untouched.

**Alternatives considered**: per-provider `include_domains` (rejected — adapter changes for marginal gain; SearXNG has no such param anyway); per-site sequential queries (rejected — N× latency for the same result).

## D4 — Domain matching (post-filter)

**Decision**: Substring matching — a result URL passes the filter if it CONTAINS any configured domain string. `microsoft.com` in the profile matches `learn.microsoft.com`, `support.microsoft.com`, etc.

**Rationale**: User decision (clarify Q4). Parent domains naturally cover subdomains; exact matching would force enumerating every subdomain.

**Alternatives considered**: exact hostname matching (rejected — user chose substring); suffix matching (rejected — substring is simpler and handles all cases the user described).

## D5 — Site normalization

**Decision**: Each site entry is normalized: strip protocol scheme (`https://`, `http://`), strip path (`/exchange/dkim`), strip leading `www.`, lowercase. Normalized at load time.

**Rationale**: Users paste URLs like `https://learn.microsoft.com/exchange` into the JSON; the tool needs just the domain for `site:` construction and substring matching. Default behavior, not worth a clarify.

**Alternatives considered**: raw-as-typed (rejected — `site:https://...` breaks SearXNG); regex-based hostname extraction (overkill — simple string ops suffice).

## D6 — Error handling matrix

| Condition | Behavior | FR |
|---|---|---|
| JSON file missing | `{"error": "no specialty profiles configured (file not found)", "profiles": {}}` | FR-004 |
| JSON malformed | `{"error": "specialty profiles file is invalid JSON: <detail>", "profiles": {}}` | FR-004 |
| Profile not found (case-insensitive) | `{"error": "profile 'X' not found", "available": {name: desc, ...}}` | FR-007 |
| Profile has empty sites | `{"error": "profile 'X' has no sites configured"}` | FR-008 |
| Scoped search returns 0 hits | Honest empty `[]` — no auto-fallback (Constitution IV) | — |
| Chain engines all down | Same error as `web_search` via `search_all` | — |

## D7 — `specialty_profiles()` companion tool

**Decision**: Returns `{name: {"sites": [...], "description": str}}` — the full JSON content. ~5 lines: read the file, return it. No arguments.

**Rationale**: User decision (clarify Q3). The Dify agent calls this first to see available profiles and their descriptions, then picks the right one for `specialty_search`.

## D8 — Integration with `web_research` and `ask`

**Decision**: Out of scope. `specialty_search` is a standalone tool; the `ask` pipeline's evidence path stays general; `web_research` doesn't gain a profile parameter.

**Rationale**: Explicitly excluded in the spec's assumptions. The agent's deliberate tool choice (not the ask pipeline's routing) is what makes specialty search valuable. Future enhancement if requested.

## D9 — Test strategy

**Decision**: Three layers:
- **Unit** (`test_specialty.py`): profile loading (missing/malformed/case-insensitive/empty-sites), site normalization, query construction (`site:a OR site:b query`), domain filter (substring, parent-matches-subdomain)
- **Contract** (`test_specialty_contract.py`): response shape pin (frozen fields + engine), existing tool canary (131-test suite unchanged)
- **Integration** (`test_specialty_integration.py`): chain mocked to a FakeProvider; `specialty_search` with a profile → results filtered to matching domains; invalid profile → honest error with available list

No live web in CI — the domain filter is testable with mocked results.

## D10 — Config surface

**Decision**: New `[web.specialty]` block in `config.toml`:
```toml
[web.specialty]
file = ""                    # path to specialty_profiles.json; empty = default
```
Default path: `~/.config/agentic-rag-mcp/specialty_profiles.json` (alongside config.toml).

**Rationale**: The path is overridable but rarely changes — one config key, no new section proliferation.
