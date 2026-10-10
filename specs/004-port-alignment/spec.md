# Feature Specification: Port Alignment — Host Port Equals Container Port

**Feature Branch**: `004-port-alignment`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Align port number (host_port:docker_container_port). Change from 28080:8080 to 28080:28080, and from 28888:8080 to 28888:28888. The purpose is to align the same port, easy to remember and straightforward to understand traffic flow."

**Blast radius (read this first)**: The AgenticRAG sidecar's container currently listens on internal port **8080**; Dify's registered MCP server URL is `http://agentic-rag:8080/mcp`. Changing the container port to 28080 changes **every Dify-internal reference** — the server must be delete + re-registered in Dify with the new URL (the edit path 500s per the known bug), and the chatflow DSL needs no URL change (it references the provider identifier, not the URL). The SearXNG container's internal port is set by the image (granian binds :8080); changing it requires setting the appropriate environment variable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aligned Sidecar Port (Priority: P1)

An operator reading the Docker mapping `-p 28080:28080` immediately knows the service is on port 28080 — inside and outside the container. No mental mapping from a published port to a different internal one. The AgenticRAG sidecar container binds port 28080 internally; the host publishes the same 28080. All existing functionality (10 MCP tools, the decision node, the reflexion loop, grouped web research) is unchanged — this is purely a listen-port change.

**Why this priority**: The sidecar is the service the user interacts with most (healthz, curl, MCP calls); aligning it delivers the core benefit immediately and makes every future deployment, debug session, and firewall rule trivial.

**Independent Test**: Start the sidecar with the new port; `curl localhost:28080/healthz` returns `{"status": "ok"}`; from a Dify container, `curl http://agentic-rag:28080/healthz` also returns `{"status": "ok"}`; all 11 tools work through the new URL.

**Acceptance Scenarios**:
1. **Given** the sidecar container is running with the aligned port, **When** `localhost:28080/healthz` is checked from the host, **Then** the health response returns correctly.
2. **Given** the sidecar is on the aligned port, **When** a Dify container connects to `http://agentic-rag:28080/mcp`, **Then** the MCP handshake completes and all 11 tools are listed.
3. **Given** the sidecar is on the aligned port, **When** the user runs `docker port agentic-rag`, **Then** the output shows `28080/tcp -> 0.0.0.0:28080` — a single number, no translation.

---

### User Story 2 - Aligned SearXNG Port (Priority: P2)

The SearXNG container binds port 28888 internally; the host publishes the same 28888. The AgenticRAG server's `[web.searxng] url` config changes from `http://searxng:8080` to `http://searxng:28888`. The JSON API check from the host is now `curl localhost:28888/search?q=test&format=json` — same port in and out.

**Why this priority**: SearXNG is the secondary service (search engine for `web_search`); aligning it is simpler (one env var + one config change) but delivers less daily value than the sidecar.

**Independent Test**: SearXNG container running on 28888; `curl localhost:28888/search?q=test&format=json` returns HTTP 200 with JSON; AgenticRAG's `web_search` tool returns live results.

**Acceptance Scenarios**:
1. **Given** SearXNG is on the aligned port, **When** `localhost:28888/search?q=test&format=json` is checked, **Then** the JSON API returns HTTP 200.
2. **Given** SearXNG is on the aligned port and AgenticRAG's config points at `http://searxng:28888`, **When** `web_search` is called through the MCP tool, **Then** live search results are returned.

---

### User Story 3 - Documentation, Skill, and Deployment Alignment (Priority: P1)

Every document, compose fragment, Dockerfile, runbook, skill, and chatflow DSL that references the old port scheme is updated to the aligned scheme. The rule becomes: **the port you see in any file, command, or URL is THE port — everywhere**.

**Why this priority**: The primary benefit is "easy to remember and straightforward to understand" — that benefit evaporates if half the docs still say 8080.

**Independent Test**: `grep -rn "8080" README.md DEPLOY.md docs/ dify/ specs/004*` returns zero hits (excluding historical specs 001-003); all compose files and run commands show `28080:28080` and `28888:28888`.

**Acceptance Scenarios**:
1. **Given** the port change is deployed, **When** `grep -rn ":8080" README.md DEPLOY.md docs/ dify/docker/` runs, **Then** zero results (excluding historical spec directories).
2. **Given** the updated compose fragments, **When** a fresh host deploys from `DEPLOY.md`, **Then** the commands produce aligned-port containers that work end to end.

---

### Edge Cases

- What happens to Dify's registered MCP server URL? (Delete + re-add with `http://agentic-rag:28080/mcp` — the edit path 500s per the known Dify bug.)
- What happens to the SSRF proxy allowlist? (Unchanged — `SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=agentic-rag` is domain-based, port-independent.)
- What happens to the Dify chatflow DSL? (No URL embedded in the tool items — the provider resolves by identifier; no DSL change needed for the port itself.)
- What happens to the AgenticRAG config's `[web.searxng] url`? (Changes from `http://searxng:8080` to `http://searxng:28888`; requires a sidecar restart.)
- What happens to scripts/run_http.py (port 8811) and run_sse.py (port 8812)? (Unchanged — these are stdio/dev transports, not the container; already non-8080.)
- What happens if someone uses the old URL during migration? (Connection refused — a clean cutover, no half-state.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The AgenticRAG sidecar container MUST listen on port **28080** internally (the same port published to the host). The `-p 28080:28080` mapping produces a single, aligned port number visible in `docker port` output.
- **FR-002**: The SearXNG container MUST listen on port **28888** internally (the same port published to the host). The `-p 28888:28888` mapping produces the same alignment.
- **FR-003**: Dify's registered MCP server URL MUST be updated to `http://agentic-rag:28080/mcp` (delete + re-add per the known edit-path bug). The SSRF allowlist is unchanged (domain-based).
- **FR-004**: The AgenticRAG config `[web.searxng] url` MUST change to `http://searxng:28888` and the sidecar MUST be restarted to pick it up.
- **FR-005**: Every committed reference to the old port scheme — README.md, DEPLOY.md, docs/NETWORK.md, dify/docker/ compose fragments, the Dockerfile EXPOSE, and the agenticrag-deploy skill — MUST be updated to the aligned scheme.
- **FR-006**: The MCP tool response contracts MUST remain unchanged (Constitution I) — only the listen port and endpoint references change, not any tool's input/output shape.
- **FR-007**: The migration MUST be a clean cutover — the old port (8080) is not left listening anywhere (host or container); there is no transition period with both ports active.

### Key Entities

- **PortSpec**: the aligned port definition — service (sidecar | searxng), host port, container port (equal by definition after this feature).
- **EndpointReference**: any URL or compose mapping that references a service's port — must be updated atomically with the PortSpec change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `docker port agentic-rag` outputs `28080/tcp -> 0.0.0.0:28080` (one number, not two).
- **SC-002**: `docker port searxng` outputs `28888/tcp -> 0.0.0.0:28888`.
- **SC-003**: 100% of the 11 MCP tools function through the new URL `http://agentic-rag:28080/mcp` after Dify re-registration (verified by tools/list + at least one ask call).
- **SC-004**: `web_search` returns live results through the aligned SearXNG port (config `http://searxng:28888`).
- **SC-005**: `grep -rn ":8080\|:8888" README.md DEPLOY.md docs/ dify/docker/` returns zero matches (the old scheme is fully gone from operational docs).
- **SC-006**: `localhost:8080` (the old port) returns connection refused — clean cutover confirmed.

## Assumptions

- The sidecar's internal listen port is controllable via the `MCP_PORT` environment variable (already implemented in `dify/docker/mcp-server/server.py`) — changing the default from 8080 to 28080 requires updating the env var or the code default.
- SearXNG's internal port is controllable via the `GRANIAN_PORT` environment variable (set in the container's env; the image honors it).
- The existing MCP tool response contracts are frozen (Constitution I); this feature changes ONLY ports and endpoint references.
- The chatflow DSL does not embed the MCP server URL (tools reference the provider identifier, not the URL); no DSL change is needed for the port itself.
- Historical specs (001–003) and their port references are immutable records and are NOT updated (they document what was true at their time).
- Out of scope: scripts/run_http.py and run_sse.py ports (dev transports, already non-8080); the Dify stack's internal ports (nginx :80, ssrf_proxy :3128 — those are Dify's, not ours).
