# Data Model: Grouped Web Research

**Feature**: specs/003-web-search-scrape/spec.md

All entities are per-request and ephemeral — nothing persists beyond the `web_research` response or the ask evidence pass (no storage changes).

## Entities

### EngineProvenance (extension to the existing provider chain)
Per-hit record of which engine produced it.

| Field | Type | Notes |
|---|---|---|
| engine | string | `searxng` \| `tavily` \| `exa` \| future adapters |
| rank | int | position as returned by that engine |

Validation (FR-001/003/004): exactly one engine per hit; dedup keeps the first-ranked URL across engines; a hit list where every engine failed carries an aggregate error state, never zero-provenance hits.

### SearchHit (extended)
The existing chain result plus provenance. **Existing fields are frozen (FR-002)**: `title`, `url`, `snippet` — byte-identical to today's `web_search` output. New (additive, research path only): `engine` (EngineProvenance).

### Block
One content unit inside a section, in document order (FR-005).

| Field | Type | Notes |
|---|---|---|
| type | enum | `p` \| `img` |
| text | string | for `p`: substantive text (>30 chars) |
| src | string | for `img`: absolute URL (urljoin-resolved); never a `data:` URI |

Validation (FR-006): paragraphs below the length floor are dropped; images without a real source are dropped; `src` must be absolute.

### PageSection
One outline unit — a heading plus its ordered blocks (FR-005).

| Field | Type | Notes |
|---|---|---|
| heading | string | from `h2`/`h3` (or page `h1` for the first section) |
| blocks | list[Block] | document order: text and its belonging image interleaved |

Validation: order is the extraction contract (SC-003: ≥90% of test-set sections preserve document order); a section with zero blocks is omitted.

### ScrapeResult
The outcome for one hit (FR-005..009, 013).

| Field | Type | Notes |
|---|---|---|
| url | string | the fetched (final, redirect-resolved) URL |
| status | enum | `ok` \| `fallback` \| `blocked` \| `failed` |
| status_reason | string \| null | e.g. `timeout`, `http:403`, `no-extractable-content`, `ssrf:blocked-private-address`, `cut-off-at-overall-bound` |
| sections | list[PageSection] | empty unless `ok` |
| truncated | bool | true when content was cut at the per-page bound (FR-007) |
| snippet | string | the search snippet — always present; it IS the content when status ≠ `ok` (honest fallback, FR-008) |

State transitions (per hit): `fetch → guard-check → (blocked) | fetch → parse → (failed/empty → fallback) | extract → (truncated) → ok`. Any non-`ok` terminal state yields the snippet as the hit's content, marked with `status_reason`.

### ResearchResult
The assembled `web_research` response (FR-011).

| Field | Type | Notes |
|---|---|---|
| query | string | as asked |
| hits | list[ResearchHit] | see below, order = search ranking |
| engines_used | list[string] | aggregate provenance (FR-003) |
| elapsed_ms | int | for SC-007 measurement |
| error | object \| null | aggregate error state when all engines failed (never fabricated hits) |

### ResearchHit
One search hit with its scrape outcome and rendering (FR-011).

| Field | Type | Notes |
|---|---|---|
| title, url, snippet, engine | (frozen fields + provenance) | identical meaning to `web_search` output |
| scrape | ScrapeResult | per-hit outcome |
| content | string | the LLM-facing text: grouped sections rendered as text (or the marked snippet fallback), bounded per page |
| render_html | string | the standalone artifact (FR-010), inline, bounded |

## Lifecycle

`web_research(query)` → chain search (provenance + dedup) → top-N hits (config `max_pages`) → bounded-parallel guarded fetches → extraction/grouping → bound/truncate → assemble ResearchResult (content + render inline) → response. Overall wall clock bounded at `overall_timeout_s` (default 30 s, FR-014); in-flight hits terminate as `fallback` with `cut-off-at-overall-bound`.

`ask` live-web evidence (FR-012): the same pipeline, internal-only — evidence items are `{title, url, snippet, content, document_id}` shaped for the reflexion Actor; sections flow into `content`; no render assembled for this path (LLM consumes text; render is review-only).
