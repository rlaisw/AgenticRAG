# Research: Grouped Web Research

**Feature**: specs/003-web-search-scrape/spec.md | **Date**: 2026-10-09

All Technical Context unknowns resolved. Constitution-gated decisions noted.

## D1 — HTTP client for page fetching: reuse httpx

**Decision**: page fetching uses **httpx** (already a project dependency, already used by `fetch_url` and the provider chain).

**Rationale**: identical capability to `requests`; Constitution III (reuse installed dependencies); one HTTP stack keeps timeouts/redirects/User-Agent behavior uniform.

**Alternatives considered**: `requests` (user's reference stack) — rejected: duplicates an installed capability. Note recorded in the spec assumption that the reference stack's *libraries* are not the requirement — the extraction rules are.

## D2 — HTML parsing: beautifulsoup4 + lxml (the only new dependencies)

**Decision**: `beautifulsoup4` + `lxml` for outline extraction. Added to `pyproject.toml` as runtime deps.

**Rationale**: the user's reference implementation names this pair; grouping requires robust `figure`/`img`/`data-src` handling and document-order traversal that stdlib `html.parser` handles poorly; lxml is the fast, tolerant parser bs4 recommends. ~5 MB wheel — acceptable for the container image.

**Alternatives considered**: stdlib `html.parser` (rejected — fragile for real-world HTML); lxml-only XPath (rejected — more code for the same grouping, harder to test).

## D3 — Parallel page fetching: bounded thread pool

**Decision**: fetch pages with a `ThreadPoolExecutor(max_workers=cfg.max_concurrent)` (default 4) inside the per-call overall bound (FR-014, 30 s default); each page has its own 15 s timeout.

**Rationale**: the MCP tool layer is synchronous; threads are the minimal concurrency change; bounded workers prevent engine hammering; the overall bound guarantees SC-007 (<30 s for 3 pages) even with slow stragglers — in-flight work is cut off with per-hit fallbacks.

**Alternatives considered**: sequential fetching (rejected: 3×15 s worst case = 45 s violates FR-014); asyncio (rejected: sync tool layer would need a rewrite; no benefit at this scale).

## D4 — SSRF guard: per-hop address resolution + ipaddress check

**Decision**: before each fetch, resolve the hostname and refuse if ANY resolved address is private, loopback, link-local, or unspecified (`ipaddress` stdlib module: `is_private | is_loopback | is_link_local | is_unspecified`, plus 169.254.169.254 metadata). Redirects are followed hop-by-hop (`follow_redirects=False` + manual Location loop, ≤3 hops) with the same check per hop — the classic bypass is a public URL redirecting to an internal one.

**Rationale**: the sidecar runs on the Dify networks (postgres, redis, ssrf_proxy are reachable); search results are partially attacker-influenced; FR-013 requires the guard; stdlib-only, no new deps. Blocked pages fall back to snippet with the block reason (honest fallback, FR-008).

**Alternatives considered**: guard at DNS-resolution time only (rejected — redirect bypass); routing all fetches through Dify's ssrf_proxy (rejected — couples the server to Dify deployments).

## D5 — Grouping rules: the reference algorithm + spec bounds

**Decision**: extraction follows the user's reference algorithm, pinned by tests: section = `h2`/`h3` heading; blocks in document order — paragraphs with >30 chars of text, `img`/`figure` images with real `src`/`data-src` (skip `data:` URIs), relative URLs absolutized via `urljoin`; main content = `article` or `main` or `body`. Spec additions: per-page content bound (default 6,000 chars, truncation flagged), document-order guarantee (SC-003 ≥90% on the test set), and empty-section tolerance (JS-only pages → fallback, never crash).

**Alternatives considered**: readability-style full-text extraction (rejected — loses the text-image grouping that is the feature's core); capturing tables/code blocks (deferred — not in spec scope).

## D6 — Test strategy + error-handling matrix (binding per user note)

**Decision**: three test layers, error paths first-class — each row of the matrix below MUST have a runnable test before the implementation that satisfies it is marked done (Constitution II):

| # | Error/fallback path (FR) | Test layer | Method |
|---|---|---|---|
| 1 | Engine down/rate-limited → next engine serves (FR-003) | unit | chain with one mocked provider raising |
| 2 | Duplicate URLs across engines deduped (FR-004) | unit | two providers return same URL |
| 3 | Page fetch timeout → snippet fallback, marked (FR-008/009) | integration | fixture server with delayed endpoint |
| 4 | HTTP 403/401 (paywall) → snippet fallback, marked (FR-008) | integration | fixture server returning 403 |
| 5 | JS-only page, no extractable content → fallback, marked (FR-008) | unit | empty-`<body>` fixture HTML |
| 6 | Private/redirect-to-private address → blocked, snippet fallback + reason (FR-013) | unit | resolver mocked to private IPs; redirect-hop case via mock Location |
| 7 | Oversized page → truncated at bound, flagged (FR-007) | unit | fixture HTML over 6,000 chars |
| 8 | `data:` URI image / relative src → skipped / absolutized (FR-006) | unit | fixture HTML |
| 9 | Document order preserved, text+image grouped (FR-005 / SC-003) | unit | fixture HTML with h2→p→img→p structure |
| 10 | All engines down → honest empty + error state (FR-003/US1-AC4) | unit | all providers raise |
| 11 | Overall bound cut-off → in-flight hits fall back (FR-014) | integration | slow fixture pages exceeding 30 s cap (reduced bound in test config) |
| 12 | `web_search` contract unchanged (FR-002 / SC-001) | contract | existing `test_web_providers` suite runs untouched |
| 13 | `web_research` response schema pinned (FR-011) | contract | schema assertion incl. provenance, flags, render |
| 14 | Renderer mirrors section order (FR-010 / SC-006) | unit | render fixture → assert headings/img/p order |

**Rationale**: the user's binding note ("create test cases and add error handling") + Constitution II; the matrix doubles as the implementation task list's acceptance spine. No live web in CI: search is mocked at the provider interface; pages come from an in-test local HTTP fixture server and file fixtures.

## D7 — Rendering: stdlib string templates, no engine

**Decision**: the renderer is a small f-string template function (the user's reference style): title, source link, sections with inline `<p>`/`<img loading="lazy">`, per-page bound respected. No template-engine dependency.

**Rationale**: Constitution III; the artifact is review-only (the LLM consumes structured sections).

**Alternatives considered**: Jinja2 (rejected — dependency for ~20 lines of markup); reusing bs4 to emit parsed trees (rejected — grouping already produces clean structures; direct templating is simpler and testable).

## D8 — Configuration surface

**Decision**: new `[web.research]` block in `config.toml` with defaults: `max_pages = 3` (cap 5), `per_page_chars = 6000`, `fetch_timeout_s = 15.0`, `overall_timeout_s = 30.0` (FR-014), `max_concurrent = 4` (D3). Engine provenance and dedup are behavior, not config (FR-001/004).

**Rationale**: all bounds in one place; no new user decisions required at runtime (defaults sensible per the spec's assumption).
