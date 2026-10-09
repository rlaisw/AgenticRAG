# Quickstart: Grouped Web Research Validation

**Feature**: specs/003-web-search-scrape/spec.md

Runnable end-to-end validation. Prerequisites: project venv, the sidecar running (host port per your config, e.g. `localhost:28080`), SearXNG reachable per `[web.searxng] url`.

## S1 — `web_research` happy path (US1/US2, FR-011)

```bash
curl -s -m 60 localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"web_research",
       "arguments":{"query":"how to trace an email in Office 365","limit":3}}}'
```

**Expected**: `hits[0].scrape.status == "ok"` with `sections` whose `blocks` interleave text and images in document order; `content` non-empty and bounded; `render_html` present; `engines_used` lists the serving engine; `elapsed_ms` present. Save `render_html` to a file and open it — sections mirror the structured output (SC-006).

## S2 — Honest fallback on a hostile page (FR-008/013)

Same call with a query that surfaces a JS-only or blocked page (or temporarily point a hit's URL at `http://127.0.0.1` via a local fixture page): **Expected** that hit shows `scrape.status == "fallback" | "blocked"` with a `status_reason`, and its `content` is the snippet — never empty, never fabricated.

## S3 — `web_search` contract frozen (FR-002 / SC-001)

```bash
.venv/bin/python -m pytest tests/contract/test_web_providers.py -q
```

**Expected**: the pre-existing suite passes unchanged (byte-identical `web_search` shape).

## S4 — Error-handling + test suite (user note; research.md D6)

```bash
.venv/bin/python -m pytest tests/ -q
```

**Expected**: all existing 99 tests plus the new research suites green — including every row of the error-handling matrix (timeouts, 403, JS-only, SSRF-blocked, truncation, dedup, engine-down, all-engines-down, render order).

## S5 — `ask` live-web evidence upgrade (FR-012)

Ask through the server: `"what time is it in hong kong"` (routes `live_web`).

**Expected**: the reflexion trace's web evidence now carries grouped `content` (structured sections) instead of a single raw page dump; citations unchanged.

## S6 — Latency (FR-014 / SC-007)

Time S1: **Expected** well under 30 s end to end for 3 pages (typical: single-digit seconds with parallel fetches).

## Notes

- Full field definitions: [contracts/web-research-tool.md](contracts/web-research-tool.md); entities and status transitions: [data-model.md](data-model.md); bounds and defaults: research.md D8 (`[web.research]` config).
- After implementation: refresh Dify's MCP tool cache (Tools → MCP → Agentic RAG → Update) so the chatflow sees `web_research`, and re-import/re-attach tools in the chatflow DSL.
