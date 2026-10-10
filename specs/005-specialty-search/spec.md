# Feature Specification: Specialty Web Search — Profile-Scoped Domain Search

**Feature Branch**: `005-specialty-search`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "I choose Option C: Configured specialty profiles. How to pre-define specialty website URLs — I prefer a JSON file, thus I can easily manage and update website URLs. Config-defined profiles with multiple sites per topic. The Dify Agentic strategy node will combine existing general web search results + results from the new specialty web search tool."

**Existing contracts (Constitution I)**: all existing tool response shapes are frozen. This feature is purely additive — a new `specialty_search` MCP tool alongside `web_search` and `web_research`.

## Clarifications

### Session 2026-10-10

- Q: How should the specialty search restrict results to the profile's sites? → A: **Option A — query-string `site:` approach**: construct `site:domain1 OR site:domain2 <query>` and pass to the existing provider chain unchanged. SearXNG forwards `site:` to Google/Bing/DDG which enforce it as a hard filter; zero adapter changes; the FR-006 post-filter guarantees domain correctness even if an engine ignores the operator. (Tavily/Exa's native `include_domains` rejected as unnecessary adapter complexity for a SearXNG-primary deployment.)
- Q: If specialty_search returns no results, should the tool auto-fallback to general search? → A: **No — the Dify agent handles the fallback.** The tool returns honest empty results (Constitution IV). The agent ALWAYS calls BOTH specialty_search AND web_search in the same reasoning turn for domain-specific questions — combining both when both have results (specialty as primary authority, general as supplementary enrichment), relying on web_search alone when specialty is empty (and telling the user the authoritative source had no match). The combination is the default, not a fallback.
- Q: How should the Dify agent discover which specialty profiles are available at runtime? → A: **Companion tool `specialty_profiles()`** — returns `{name: {sites, description}}` from the JSON file on every call (~5 lines, always current, zero staleness). The agent calls it first to see available profiles, then calls `specialty_search` with the right profile name. FR-009 updated accordingly.
- Q: If a profile lists a parent domain like `microsoft.com`, should results from `learn.microsoft.com` (a subdomain) also be included? → A: **Substring matching** (user decision, 2026-10-10) — a configured domain matches any URL *containing* that domain string (parent `microsoft.com` matches `learn.microsoft.com`, `support.microsoft.com`). Rationale: profiles list parent domains for manageability and expect all subdomains to match; exact-domain matching would force enumerating every subdomain, defeating the "easy to manage" goal. FR-006's domain check is substring-based.
- Q: For multiple topics (e.g., Microsoft, Huawei, vibe coding, AI), should there be multiple tools or one tool with multiple profiles? → A: **One tool + multiple profiles** (user confirmed, 2026-10-10) — a single `specialty_search(query, profile)` tool; each topic is a separate profile entry in the JSON file. The agent calls `specialty_profiles()` to discover available topics, then picks the right profile by name. Adding a new topic = editing the JSON file (hot-reload, no code changes, no Dify cache refresh). Confirmed with 4 example profiles: microsoft, huawei, vibe_coding, ai.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Profile-Scoped Search (Priority: P1)

A user asks a domain-specific question: "How do I configure DKIM in Exchange Online?" The Dify agent recognizes this as a Microsoft-product question and calls `specialty_search(query, profile)` with the "microsoft" profile — which scopes the search to `learn.microsoft.com` and `techcommunity.microsoft.com` via `site:` operators. Results come exclusively from the configured authoritative domains, not from random blog posts or SEO spam. The agent also calls `web_search` with the same question for broader context, then synthesizes both result sets — the specialty results as the authoritative primary, the general results as supplementary.

**Why this priority**: This is the entire feature — scoped search returning authoritative results from pre-defined sites, combined with general search by the agent.

**Independent Test**: Call `specialty_search("DKIM Exchange Online", "microsoft")` — every result URL must contain at least one of the profile's configured domains. Call with an invalid profile name — get an honest error listing available profiles.

**Acceptance Scenarios**:

1. **Given** a specialty profile "microsoft" with sites `["learn.microsoft.com", "techcommunity.microsoft.com"]`, **When** `specialty_search("DKIM", "microsoft")` is called, **Then** every returned hit's URL contains at least one of the configured domains.
2. **Given** an invalid profile name "nonexistent", **When** `specialty_search(query, "nonexistent")` is called, **Then** the response carries an honest error listing the available profile names — never an empty result masquerading as success.
3. **Given** a profile with no sites configured (empty list), **When** the tool is called, **Then** the response says "profile has no sites configured" — never a general unscoped search.
4. **Given** the general search chain is down, **When** `specialty_search` is called, **Then** the same honest error/fallback applies as `web_search` (Constitution IV).

---

### User Story 2 — JSON-Managed Profiles (Priority: P1)

The operator manages specialty profiles in a **JSON file** (e.g., `~/.config/agentic-rag-mcp/specialty_profiles.json`), separate from the main config.toml. Adding a new specialty topic is a file edit — no code changes, no server restart needed to pick up changes (hot-reload on next tool call). Each profile has a name, a human-readable description (so the Dify agent knows when to use it), and a list of site domains.

**Example JSON file**:
```json
{
  "microsoft": {
    "sites": ["learn.microsoft.com", "techcommunity.microsoft.com", "support.microsoft.com"],
    "description": "Microsoft product documentation, community, and support"
  },
  "security": {
    "sites": ["owasp.org", "nist.gov", "cve.mitre.org"],
    "description": "Security standards, advisories, and vulnerability databases"
  },
  "python_dev": {
    "sites": ["docs.python.org", "realpython.com", "stackoverflow.com"],
    "description": "Python documentation and community Q&A"
  }
}
```

**Why this priority**: The user explicitly chose JSON for manageability — this is the core user experience.

**Independent Test**: Add a new profile to the JSON file → call `specialty_search` with it on the next request → results are scoped to the new profile's sites (no restart needed).

**Acceptance Scenarios**:

1. **Given** the JSON file contains profiles, **When** the server starts, **Then** `specialty_search` can use every profile by name.
2. **Given** the server is running and a new profile is added to the JSON file, **When** `specialty_search` is called with the new profile name, **Then** the new profile is recognized (hot-reload, no restart).
3. **Given** the JSON file is missing or malformed, **When** the server runs, **Then** the tool returns an honest "no specialty profiles configured" error — never a crash.
4. **Given** a profile has a `description` field, **When** the Dify agent sees the tool's available profiles, **Then** the description helps the agent choose the right profile for the question's topic.

---

### User Story 3 — Agent Integration: Combined Reasoning (Priority: P2)

The Dify Agentic Strategy node (FunctionCalling) calls both `specialty_search` and `web_search` in the same reasoning turn, synthesizes the results — specialty as authoritative, general as supplementary — and cites both. The agent's instruction is updated to know when to prefer specialty vs general.

**Why this priority**: The agent-side integration is instructions + tool attachment in the chatflow — the Dify-side work after the server-side tool is live.

**Independent Test**: Ask the chatflow a domain-specific question ("How do I configure DKIM in Exchange Online?") → the answer cites results from learn.microsoft.com (specialty) AND broader sources (general), with the Microsoft docs as the primary authority.

**Acceptance Scenarios**:

1. **Given** both `specialty_search` and `web_search` are attached to the agent node, **When** a domain-specific question arrives, **Then** the agent calls both tools and synthesizes — specialty results ranked as primary.
2. **Given** a general question with no matching specialty profile, **When** the agent reasons, **Then** it uses `web_search` only — no forced specialty call.

---

### Edge Cases

- What if the profile's sites produce zero hits? (Honest empty result from the scoped search — the agent can fall back to `web_search`.)
- What if a site domain is misspelled or unreachable? (SearXNG handles it — returns no results for that site; no crash.)
- What if the JSON file has duplicate profile names? (Last one wins — JSON dict semantics; a warning is logged.)
- What if a profile has sites but the engine is down? (Same fallback chain as general search — next engine serves.)
- What if the user passes a profile name with different casing? (Case-insensitive profile lookup — "Microsoft" and "microsoft" resolve to the same profile.)
- What if the JSON file is replaced while a search is in-flight? (The in-flight search uses the profile loaded at request start; the next request sees the new file.)

## Requirements *(mandatory)*

### Functional Requirements

**Profile management**

- **FR-001**: Specialty profiles MUST be defined in a JSON file (default path alongside the main config, overridable in config) with each profile containing: a name (the JSON key), a list of site domains, and a human-readable description.
- **FR-002**: Profile definitions MUST be hot-reloaded — changes to the JSON file are visible on the next `specialty_search` call without a server restart.
- **FR-003**: Profile name lookup MUST be case-insensitive ("Microsoft" = "microsoft").
- **FR-004**: A missing or malformed JSON file MUST NOT crash the server — the tool returns an honest "no specialty profiles configured" error on every call.

**Specialty search**

- **FR-005**: A new `specialty_search(query, profile, limit)` MCP tool MUST scope search results to the profile's configured sites using domain restriction, returning the same result shape as `web_search` (title, url, snippet) plus engine provenance — additive, no existing tool changes.
- **FR-006**: Every returned result's URL MUST contain at least one of the profile's configured site domains as a substring (parent domains match their subdomains — decided in Clarifications) — if a result's URL doesn't contain any configured domain, it MUST be filtered out.
- **FR-007**: An invalid or unknown profile name MUST return an honest error listing available profile names and their descriptions.
- **FR-008**: A profile with an empty sites list MUST return an honest error — never a general unscoped search.
- **FR-009**: A companion `specialty_profiles()` tool MUST return the current profile names, sites, and descriptions (from the JSON file, always current — hot-reload guaranteed), so the Dify agent can discover available profiles before calling `specialty_search`.

**Agent integration**

- **FR-010**: The Dify agent's instruction MUST be updated to describe when to use `specialty_search` vs `web_search`, and to combine both when a domain-specific question arrives.
- **FR-011**: The chatflow DSL MUST attach `specialty_search` to the Agent node alongside the existing tools.

### Key Entities

- **SpecialtyProfile**: one named profile — name (case-insensitive key), sites (list of domain strings), description (for agent discovery).
- **ProfileFile**: the JSON file containing all profiles — path, hot-reload semantics, error tolerance for missing/malformed content.
- **SpecialtySearchResult**: same shape as a general web search hit (title, url, snippet, engine) — with the guarantee that every url matches at least one profile site.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `specialty_search` results have URLs containing at least one configured site domain, across all profiles and test queries.
- **SC-002**: A new profile added to the JSON file is usable on the very next `specialty_search` call — zero restarts (hot-reload verified).
- **SC-003**: An invalid profile name returns available profiles with descriptions in 100% of test cases — never silent or empty.
- **SC-004**: All existing tool response shapes remain unchanged (Constitution I) — the 131-test suite passes untouched.
- **SC-005**: The Dify agent, asked a domain-specific question, calls both `specialty_search` and `web_search` and cites the specialty source as primary authority.

## Assumptions

- The JSON file lives at `~/.config/agentic-rag-mcp/specialty_profiles.json` by default; the path is overridable in config.toml (`[web.specialty] file = "..."`).
- Domain scoping uses the search engine's native `site:` operator — already supported by SearXNG (and by Tavily/Exa through their APIs if they're configured).
- Result dedup and provenance reuse the existing `search_all` chain — no new search logic.
- The tool returns the same result shape as `web_search` (plus `engine` provenance) — Constitution I compliant.
- Hot-reload reads the JSON file on every `specialty_search` call (cheap file read; no in-memory cache to invalidate).
- Out of scope: scraping/authenticating to profile sites (the sites are just search-domain filters); per-profile engine selection (all profiles use the same engine chain); `web_research` integration with profiles (future enhancement if requested).
