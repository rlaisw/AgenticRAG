# Data Model: Specialty Web Search

**Feature**: specs/005-specialty-search/spec.md

## Entities

### SpecialtyProfile
One named profile — a set of authoritative domains with a description.

| Field | Type | Validation | Notes |
|---|---|---|---|
| name | string | JSON key; case-insensitive lookup key | "Microsoft" and "microsoft" resolve to the same profile |
| sites | list[str] | each entry normalized: strip scheme, path, `www.`; lowercase | the domains to scope search to |
| description | string | non-empty (for agent discovery) | shown in `specialty_profiles()` output and error listings |

### ProfileFile
The JSON file containing all profiles.

| Field | Type | Notes |
|---|---|---|
| path | Path | default `~/.config/agentic-rag-mcp/specialty_profiles.json`; overridable via `[web.specialty] file` |
| format | dict[str, dict] | `{name: {"sites": [...], "description": str}}` |
| reload | per-call | read on every `specialty_search` / `specialty_profiles` invocation (hot-reload) |
| error_tolerance | non-fatal | missing file → `"no specialty profiles configured"`; malformed JSON → honest error with detail |

### SpecialtySearchResult
Same shape as a general web search hit plus the domain-match guarantee.

| Field | Type | Notes |
|---|---|---|
| title, url, snippet, engine | (frozen fields + provenance) | identical meaning to `web_search`/`search_all` output |
| guarantee | FR-006 | every `url` contains at least one profile site domain (substring match — decided in Clarifications) |

## State Transitions

```
specialty_search(query, profile, limit):
  1. load profiles (JSON file, per-call read)
       ├─ missing/malformed → honest error (FR-004) → STOP
  2. resolve profile (case-insensitive)
       ├─ not found → honest error + available profiles (FR-007) → STOP
       ├─ empty sites → honest error (FR-008) → STOP
  3. normalize sites (strip scheme/path/www, lowercase)
  4. construct query: "site:dom1 OR site:dom2 ... <query>"
  5. search_all(providers, scoped_query, limit)  ← existing chain
  6. post-filter results: keep only URLs containing a configured domain (substring, FR-006)
  7. return filtered results (honest empty if nothing survives the filter)
```

## Site normalization rules (research.md D5)

| Input (as typed by user) | Normalized |
|---|---|
| `https://learn.microsoft.com/exchange` | `learn.microsoft.com` |
| `http://www.owasp.org` | `owasp.org` |
| `docs.python.org` | `docs.python.org` (already clean) |
| `HTTPS://NIST.GOV` | `nist.gov` (lowercased) |
| `learn.microsoft.com/` | `learn.microsoft.com` (trailing slash stripped) |
