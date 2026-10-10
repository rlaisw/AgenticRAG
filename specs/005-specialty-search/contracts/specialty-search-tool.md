# Contract: `specialty_search` + `specialty_profiles` MCP Tools

**Feature**: specs/005-specialty-search/spec.md | FR-001..FR-011

New, additive MCP tools. All existing tool response shapes are UNCHANGED (Constitution I / SC-004).

## `specialty_search(query, profile, limit)`

### Request

```json
{"query": "DKIM Exchange Online", "profile": "microsoft", "limit": 5}
```

| Arg | Type | Default | Constraint |
|---|---|---|---|
| query | string | required | the user's question |
| profile | string | required | case-insensitive profile name (must exist in the JSON file) |
| limit | int | 5 | max results |

### Response (success)

```json
[
  {"title": "Configure DKIM...", "url": "https://learn.microsoft.com/en-us/exchange/dkim",
   "snippet": "Use Set-DkimSigningConfig...", "engine": "searxng"}
]
```

Same shape as `web_search` output plus `engine` provenance. **Guarantee (FR-006)**: every `url` contains at least one of the profile's configured domain strings (substring match).

### Response (error — honest, never silent)

| Condition | Response |
|---|---|
| Profile not found | `{"error": "profile 'X' not found", "available": {"microsoft": "Microsoft product docs", "security": "Security standards"}}` |
| Empty sites | `{"error": "profile 'X' has no sites configured"}` |
| File missing | `{"error": "no specialty profiles configured (file not found)"}` |
| Malformed JSON | `{"error": "specialty profiles file is invalid JSON: <detail>"}` |
| 0 scoped results | `[]` — honest empty; the agent falls back to `web_search` (Clarifications) |

## `specialty_profiles()`

### Request
No arguments.

### Response (success)

```json
{
  "microsoft": {"sites": ["learn.microsoft.com", "techcommunity.microsoft.com", "support.microsoft.com"],
                 "description": "Microsoft product documentation, community, and support"},
  "security": {"sites": ["owasp.org", "nist.gov", "cve.mitre.org"],
                "description": "Security standards, advisories, and vulnerability databases"}
}
```

### Response (error)
Same honest-error table as `specialty_search` (file-level errors are shared).

## Invariants

1. **Contract freeze** (SC-004): the 131-test suite passes unchanged; `web_search`/`web_research`/`fetch_url`/`ask` are untouched.
2. **Domain guarantee** (FR-006 / SC-001): 100% of `specialty_search` results have URLs containing a configured domain (substring match — parent matches subdomains).
3. **Hot-reload** (SC-002): a profile added to the JSON file is usable on the very next call — zero restarts.
4. **Honest errors** (FR-004/007/008 / SC-003): every failure mode returns an explicit error — never silent, never fabricated, never an unscoped search masquerading as scoped.
5. **Case-insensitive** (FR-003): `"Microsoft"` and `"microsoft"` resolve to the same profile.
6. **Same-chain latency**: `specialty_search` goes through the identical provider chain as `web_search` — no added latency beyond the domain post-filter (~microseconds for ≤5 results).
