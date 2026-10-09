# Feature Specification: Grouped Web Research — Multi-Engine Search with Outline-Preserving Page Scraping

**Feature Branch**: `003-web-search-scrape`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Enhance the SearXNG to give a nice and useful output result to pass to LLM. Objective: searches the web using litellm multi-engine support and then scrapes each page found [searxng][tavily][exa][perplexity]. Instead of showing all text then all images separately, it preserves the original page outline and displays the text + the image that belongs to that text grouped together in the same section, in document order: <h2> → <p> → img → <p>. Stack: litellm for search, requests + beautifulsoup4 + lxml for scraping and grouping, and HTML rendering to display the result similar to the original web page." (Full reference implementation quoted verbatim in the triggering message.)

**Existing contracts (Constitution I)**: the `web_search` MCP tool's response — `[{title, url, snippet}]` — is a ratified client contract with passing contract tests. This feature is ADDITIVE: that shape must not change. Grouped research surfaces as a **new `web_research` MCP tool** (decided — see Clarifications).

## Clarifications

### Session 2026-10-09

- Q: Adopt litellm as the unified search facade, or keep the existing provider chain (searxng/tavily/exa adapters)? → A: **KEEP the existing provider chain — litellm is NOT adopted** (user decision, 2026-10-09). Evidence recorded: litellm adds 23 transitive packages (incl. the AWS SDK) for three stable ~30-line REST calls the chain already performs; litellm's search API is single-provider-per-call so the fallback chain remains our code either way; env-var-only config conflicts with config.toml; Constitution III (minimal dependencies) and V (replacement needs spec'd justification) both favor retention. Additional engines (e.g. perplexity) join as small adapters on the existing pattern, gated by their API keys.
- Q: Should grouped web research surface as a new `web_research` MCP tool, or as additive fields on the existing `web_search` tool? → A: **New `web_research(query, limit)` MCP tool** (user decision, 2026-10-09) — it composes the existing provider chain for search, then adds scrape + grouping + rendering; `web_search`'s response stays byte-identical (Constitution I, zero regression risk), and the agent picks per task: snippet lookups (`web_search`) vs. page-level grouped research (`web_research`).
- Q: Where should the rendered HTML artifact live — inline in the response, or written to a server-side output directory? → A: **Returned inline in the `web_research` response** (user decision, 2026-10-09) — the response is the only channel that reaches MCP callers (the Dify agent and, through it, the chatflow user); container-side files are invisible to them. The LLM ignores the HTML field (it consumes the structured sections); the per-page bound keeps the response size sane; callers save or forward the artifact as needed.
- Q: Should the `ask` pipeline's live-web reasoning also consume grouped page content, or is the `web_research` tool the only consumer? → A: **Both consumers** (user decision, 2026-10-09) — the System 2 reflexion loop's live-web evidence upgrades to grouped scraping (replacing the prior single-page fetch enrichment), so ask answers benefit from the same bounded, structured sections; the evidence shape is internal, so no client contract is affected.
- Q: Should the server block scraped fetches to private/internal network addresses (SSRF guard), or fetch whatever URL the search returns? → A: **Guard** (user decision, 2026-10-09) — scraped targets are resolved and private/loopback/link-local addresses are refused; a blocked page falls back to its snippet, marked with the block reason. The sidecar runs on the Dify networks where internal services live, so the guard closes a real request-forgery surface. The pre-existing `fetch_url` tool's identical exposure is noted as a separate follow-up, out of this feature's scope.
- Q: What end-to-end latency target should `web_research` have for a typical 3-page research call? → A: **Under 30 seconds** (user decision, 2026-10-09) — the bound covers search, page fetching, grouping, and rendering together; work still in flight at the bound is cut off with honest per-hit fallbacks rather than extending the wait.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Engine Live Search (Priority: P1)

A question arrives that the knowledge base cannot answer ("how to trace an O365 email"). The system searches the live web through a configured engine chain: the self-hosted engine first (free), then commercial engines (when their keys are configured), optionally an answer-style engine as an additional source. Results carry the fields clients already depend on — title, url, snippet — plus the engine that produced each hit. If one engine is down or rate-limited, the next engine serves the request; a search never fails because a single engine did. Duplicate URLs across engines appear once.

**Why this priority**: every downstream capability (scraping, grouping, rendering) depends on a dependable, broad search layer; and the existing web tool is already in production use by the chatflow, so its contract must hold from the first release.

**Independent Test**: Fully testable by issuing live questions with one engine forcibly disabled — results still arrive, provenance shows the serving engine, and the prior field set is unchanged (regression suite green).

**Acceptance Scenarios**:

1. **Given** a live-data question, **When** the search runs, **Then** results include title, url, and snippet for every hit, plus the contributing engine.
2. **Given** one configured engine fails or times out, **When** the search executes, **Then** the next engine serves the request and the response records which engines contributed.
3. **Given** the same URL is returned by two engines, **When** results are assembled, **Then** it appears exactly once, keeping the first ranking.
4. **Given** no engine is reachable, **When** the search executes, **Then** the system returns an honest empty result with a clear error state — never fabricated results.

---

### User Story 2 - Outline-Preserving Grouped Page Content for the LLM (Priority: P1)

For each search result (up to a configured bound), the system fetches the page and extracts its content as ordered sections that preserve the original outline: a heading, then its text and the images belonging to that text, interleaved in document order — never "all text, then all images". Extraction keeps only substantive paragraphs and real image sources (no embedded data-images, no tracking pixels), and resolves relative image URLs to absolute ones. The grouped sections — not a raw page dump — are what gets passed to the LLM, bounded per page so one huge page cannot consume the whole context. When a page can't be fetched or parsed (timeout, JavaScript-only page, paywall), the system falls back to the search snippet for that result, marked as a fallback — content is never silently missing and never invented (Constitution IV).

**Why this priority**: this is the user's core objective — "a nice and useful output to pass to the LLM" — and the grouped structure is what makes scraped pages actually usable as agent evidence instead of noise.

**Independent Test**: Fully testable against a fixed set of content pages with known structure — assert the extracted sections preserve document order and that text + belonging image land in the same section; and against unfetchable pages — assert the snippet fallback fires.

**Acceptance Scenarios**:

1. **Given** a result page with heading → paragraph → image → paragraph structure, **When** it is scraped, **Then** the extracted section contains the paragraph, then the image, then the next paragraph — in original document order.
2. **Given** a page whose main content cannot be located, **When** extraction runs, **Then** the section list may be empty and the result is marked for fallback to the snippet.
3. **Given** a page that times out or rejects fetching, **When** the research completes, **Then** that result carries its search snippet, marked as a fallback — not an empty entry.
4. **Given** a page whose extracted content exceeds the configured per-page bound, **When** grouping completes, **Then** the content is truncated at the bound and the truncation is flagged.
5. **Given** images with relative sources or embedded data URIs, **When** extraction runs, **Then** relative sources are resolved to absolute URLs and data URIs are skipped.

---

### User Story 3 - Human-Readable Rendering of Grouped Results (Priority: P3)

The grouped sections render as a clean, standalone HTML artifact mirroring the original page's structure: document title, a link to the source, then each section with its heading, paragraphs, and belonging images displayed inline — so a human can review exactly what the LLM saw, in reading order.

**Why this priority**: the LLM consumes the structured sections; rendering is review/diagnostic value — useful but not load-bearing for answer quality.

**Independent Test**: Fully testable by opening a rendered artifact in a browser and verifying its sections match the structured output in content and order.

**Acceptance Scenarios**:

1. **Given** a completed grouped research result, **When** it is rendered, **Then** the artifact opens standalone in a browser and displays title, source URL, and every section with its text and images inline.
2. **Given** a result that fell back to snippet, **When** rendered, **Then** the artifact shows the snippet text with a visible fallback marker.

---

### Edge Cases

- What happens when a page is JavaScript-only with no extractable content? (Section extraction yields nothing → snippet fallback, marked.)
- What happens on a page behind authentication or a paywall? (Fetch rejected → snippet fallback, marked.)
- What happens when one page is very slow? (Per-page fetch timeout bounds the wait; that page falls back, others proceed.)
- What happens when an engine is rate-limited mid-session? (Next configured engine serves; provenance records it.)
- What happens when the same page is found by multiple engines? (Dedup by URL, first ranking kept.)
- What happens when a page has hundreds of sections? (Truncation at the configured per-page bound, flagged.)
- What happens when all engines fail? (Honest empty result with error state — never fabricated.)
- What happens when a search result points at a private/internal address? (SSRF guard blocks the fetch; the hit falls back to its snippet, marked with the block reason — FR-013.)

## Requirements *(mandatory)*

### Functional Requirements

**Search (Constitution I — additive)**

- **FR-001**: The web search MUST query the configured engine set in order (self-hosted engine first; commercial and answer-style engines only when their credentials are configured) and return results carrying the existing field set (title, url, snippet) plus the contributing engine.
- **FR-002**: The response shape of the existing web search tool MUST remain unchanged for existing consumers; grouped-research capabilities MUST surface as new fields or a new, additive tool.
- **FR-003**: Any single engine failure, timeout, or rate limit MUST NOT fail the search; the next engine serves, and the response records engine provenance.
- **FR-004**: Results returned by multiple engines MUST be deduplicated by URL, keeping the first ranking.

**Grouped extraction (Constitution IV — honest)**

- **FR-005**: For each scraped result page, the system MUST extract ordered sections that preserve the original document outline: a section is a heading plus its content blocks — paragraphs and the images belonging to that text — interleaved in document order.
- **FR-006**: Extraction MUST keep only substantive text blocks and real image sources: embedded data-URI images are skipped, and relative image URLs are resolved to absolute.
- **FR-007**: The grouped content passed onward MUST be bounded by a configurable per-page cap; truncated output MUST be flagged as truncated.
- **FR-008**: An unfetchable or unparseable page MUST fall back to its search snippet, explicitly marked as fallback — never silently omitted, never fabricated.
- **FR-009**: Each page fetch MUST respect a per-page timeout so a single slow page cannot stall the research request; the overall search respects per-engine timeouts.

**Rendering**

- **FR-010**: Grouped results MUST render as a standalone HTML artifact mirroring the grouped structure (title, source link, sections with inline text + belonging images), returned inline in the research response within the per-page bound — openable in any browser without a server once saved by the caller (decided: no server-side file output).
- **FR-011**: A new research tool — working name `web_research(query, limit)` — MUST expose grouped research end to end: it MUST reuse the existing provider chain for search (no duplicated search logic) and return, per hit, the grouped sections (or the explicitly marked snippet fallback per FR-008), truncation flags per FR-007, engine provenance per FR-001, and the rendered artifact per FR-010.
- **FR-012**: The `ask` pipeline's live-web evidence MUST consume grouped page content (per FR-005..009), replacing the prior single-page enrichment, so reflexion drafts are built from bounded, structured sections. The evidence shape is internal — no client-facing contract changes (Constitution I).
- **FR-013**: Page fetches MUST resolve the target address and refuse private, loopback, and link-local destinations (SSRF guard); a blocked page falls back to its snippet, marked with the block reason, per the honest-fallback rule (FR-008).
- **FR-014**: A typical research call (3 pages) MUST complete end to end — search, fetching, grouping, and rendering — within the configured overall bound (default 30 seconds); work still in flight at the bound is cut off with honest per-hit fallbacks rather than extending the wait.

### Key Entities

- **EngineConfig**: a configured search engine — name, endpoint/credentials reference, enabled flag, position in the fallback order.
- **SearchHit**: one result — title, url, snippet, plus the contributing engine and rank.
- **PageSection**: one outline unit — heading plus an ordered list of blocks, each block being text or an image reference.
- **ScrapeResult**: the outcome for one hit — url, ordered sections, status (`ok` | `fallback` | `failed`), truncated flag, and the rendered artifact when requested.
- **ResearchResult**: the assembled output — the search hits with their scrape results, provenance, and the bounded, grouped content ready for the LLM.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of web-search responses retain the prior field set (title, url, snippet) across the existing regression suite — no existing consumer breaks.
- **SC-002**: With one engine forcibly disabled, ≥95% of test queries still return results, and 100% of responses record which engine served them.
- **SC-003**: On a 10-page structured-content test set, ≥90% of extracted sections preserve document order with text and belonging image grouped in the same section.
- **SC-004**: 100% of attempted results yield LLM-usable content — grouped sections or an explicitly marked snippet fallback.
- **SC-005**: 100% of grouped page outputs stay within the configured per-page bound, with truncation flagged whenever it occurs.
- **SC-006**: A rendered artifact opens standalone in a browser and presents the same sections, in the same order, as the structured output (verified on the test set).
- **SC-007**: At least 95% of typical research calls (3 pages) complete within 30 seconds end to end, including search, fetching, grouping, and rendering.

## Assumptions

- **Search layer (decided — see Clarifications)**: the existing provider chain (searxng/tavily/exa adapters, fallback order in config.toml) is retained and extended; litellm is not adopted. New engines (e.g. perplexity) are added as adapters on the existing pattern when their keys are configured.
- The self-hosted engine remains the free, primary source; commercial/answer engines activate only when credentials are configured in `config.toml`.
- The scraping stack honors the user's reference (HTTP client + HTML parser); the plan may substitute the project's existing HTTP client for equivalent behavior — the extraction/grouping rules are the requirement, the libraries are not.
- The LLM consumes the structured sections; the rendered HTML is for human review and diagnostics.
- Per-page bound and timeouts get sensible defaults (documented in config) rather than new user decisions.
- Out of scope: headless-browser JavaScript execution, downloading/storing media files, changes to knowledge-base ranking, the `fetch_url` tool's live-clock contract, and guarding the pre-existing `fetch_url` tool against private-address targets (separate follow-up — FR-013 covers this feature's fetches only).
