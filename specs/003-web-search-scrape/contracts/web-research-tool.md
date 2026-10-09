# Contract: `web_research` MCP Tool

**Feature**: specs/003-web-search-scrape/spec.md | FR-001, FR-002, FR-004..FR-011, FR-013, FR-014

New, additive MCP tool. The existing `web_search` contract is UNCHANGED — its response stays exactly `[{title, url, snippet}]` (SC-001, pinned by the existing `test_web_providers.py` suite).

## Request

```json
{ "query": "how to trace an email in Office 365", "limit": 3 }
```

| Arg | Type | Default | Constraint |
|---|---|---|---|
| query | string | required | the user's question verbatim |
| limit | int | 3 | capped at 5 (config `max_pages`) |

## Response: ResearchResult

```json
{
  "query": "how to trace an email in Office 365",
  "engines_used": ["searxng"],
  "elapsed_ms": 8123,
  "error": null,
  "hits": [
    {
      "title": "…", "url": "https://…", "snippet": "…", "engine": "searxng",
      "scrape": {
        "url": "https://…",
        "status": "ok", "status_reason": null,
        "sections": [
          { "heading": "Trace a message",
            "blocks": [
              { "type": "p", "text": "In the Exchange admin center, open message trace…" },
              { "type": "img", "src": "https://…/trace.png" }
            ]}
        ],
        "truncated": false,
        "snippet": "…"
      },
      "content": "Trace a message\nIn the Exchange admin center…",
      "render_html": "<html>…sections in document order…</html>"
    }
  ]
}
```

## Invariants

1. **Contract freeze (FR-002 / SC-001)**: `web_search` responses are byte-identical to today's; this tool adds no fields to it.
2. **Every hit yields content (FR-008 / SC-004)**: `content` is never empty — grouped sections when `scrape.status == "ok"`, else the snippet, with `status_reason` set (`timeout`, `http:403`, `no-extractable-content`, `ssrf:blocked-private-address`, `cut-off-at-overall-bound`).
3. **Order (FR-005 / SC-003)**: `sections[].blocks` preserve document order — text and its belonging image interleaved, never all-text-then-all-images.
4. **Bounds (FR-007 / SC-005)**: per-hit content and `render_html` respect the per-page char bound; `truncated: true` whenever cut.
5. **Guard (FR-013)**: private/loopback/link-local destinations (including via redirects) return `scrape.status == "blocked"` with the reason — never fetched.
6. **Latency (FR-014 / SC-007)**: `elapsed_ms` present; ≥95% of 3-page calls under 30,000 ms; in-flight work at the bound ends as honest fallbacks, never a hang.
7. **Honest empties (US1-AC4)**: all engines down → `hits: []` with a non-null `error` object — no fabricated hits.
8. **Provenance (FR-001/003)**: every hit carries its `engine`; `engines_used` aggregates; duplicate URLs across engines appear once (first ranking).
9. **Render mirrors structure (FR-010 / SC-006)**: `render_html` is standalone HTML (title, source link, sections with inline text + images), openable without a server; section order matches `sections`.

## Internal consumer note (FR-012)

The `ask` pipeline's live-web evidence uses the same pipeline but an internal shape (`content` per evidence item; no render) — this is not a client contract and may evolve.
