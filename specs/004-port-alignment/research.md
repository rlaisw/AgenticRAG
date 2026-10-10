# Research: Port Alignment

**Feature**: specs/004-port-alignment/spec.md | **Date**: 2026-10-10

All Technical Context unknowns resolved. Zero NEEDS CLARIFICATION.

## D1 — Sidecar container port: MCP_PORT environment variable

**Decision**: Set `-e MCP_PORT=28080` in the `docker run` command (or change the code default in `dify/docker/mcp-server/server.py` from `"8080"` to `"28080"`). The `-p 28080:28080` mapping produces the aligned port.

**Rationale**: The sidecar server already reads `MCP_PORT` from the environment (line 18 of server.py: `PORT = int(os.environ.get("MCP_PORT", "8080"))`). Changing the default in the code is the cleaner option — it eliminates the need to remember the env var on every `docker run` and makes the compose fragments self-documenting.

**Alternatives considered**: env-var-only (rejected: requires remembering `-e` on every deployment); compose-only override (rejected: bare `docker run` wouldn't get the right port).

## D2 — SearXNG container port: GRANIAN_PORT environment variable

**Decision**: Set `-e GRANIAN_PORT=28888` on the SearXNG container (the image uses granian as its HTTP server; the port is configurable via this env var, confirmed from the container's existing env: `"GRANIAN_PORT=8080"`).

**Rationale**: The SearXNG image already sets `GRANIAN_PORT=8080` internally; overriding it via Docker env is the standard supported path. No image rebuild needed.

**Alternatives considered**: none — this is the only mechanism the image provides.

## D3 — AgenticRAG `[web.searxng] url` config

**Decision**: Update `~/.config/agentic-rag-mcp/config.toml` to `[web.searxng] url = "http://searxng:28888"` (was `:8080`). The DEFAULT_CONFIG comment in `src/agentic_rag_mcp/config.py` stays generic (the URL is user-configured, not a default).

**Rationale**: The provider chain reads this URL at server start; a sidecar restart picks it up.

**Alternatives considered**: none.

## D4 — Dify MCP server re-registration

**Decision**: Delete the existing "Agentic RAG" entry in Dify → Tools → MCP → re-add with `http://agentic-rag:28080/mcp` (no headers, no DCR, identifier `agentic-rag`). The SSRF allowlist (`SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=agentic-rag`) is unchanged (domain-based, port-independent).

**Rationale**: The edit-path 500s (identifier-vs-UUID bug); delete + re-add is the only supported method. The chatflow DSL tools reference the identifier (`provider_name: agentic-rag`), not the URL — they re-resolve automatically after re-registration.

**Alternatives considered**: editing the URL in the Dify DB directly (rejected — fragile, bypasses the tool-listing flow).

## D5 — Dockerfile EXPOSE

**Decision**: Change `EXPOSE 8080` to `EXPOSE 28080` in `dify/docker/mcp-server/Dockerfile`. Purely documentation (EXPOSE is informational), but keeps the file honest.

**Rationale**: A stale EXPOSE misleads readers about the actual port.

## D6 — Documentation sweep scope

**Decision**: Update every committed port reference in:
- `README.md` (docker run example + config comments)
- `DEPLOY.md` (Step 3 docker run, Step 4 Dify URL, Step 5 SearXNG, port card)
- `docs/NETWORK.md` (diagram, connection matrix, port card, troubleshooting table)
- `dify/docker/mcp-server/docker-compose.yml` (ports line)
- `dify/docker/mcp-server/server.py` (docstring)
- `dify/docker/mcp-server/Dockerfile` (EXPOSE)
- `dify/docker/docker-compose.yml` (ports if referenced)
- `~/.config/kilo/skills/agenticrag-deploy/SKILL.md` (user-level skill, not committed but should stay in sync)
- `DEPLOY.md` → the committed copy, NOT the Downloads copy (the user's Downloads chatflow YAML doesn't embed ports)

Historical specs (001–003) are NOT updated — they are immutable records.

**Rationale**: FR-005 demands full alignment; SC-005 verifies with grep.

## D7 — Test suite impact

**Decision**: None. The 131-test suite uses in-process `server.call_tool()`, never HTTP — no port is involved. No test changes, no new tests.

**Rationale**: The port is a deployment concern, not a code contract.

## D8 — Rollback

**Decision**: Document the rollback path: revert the `docker run` command (change `-p` and `-e` back), revert the config.toml URL, restart, delete + re-add the Dify entry with the old URL. ~5 minutes.

**Rationale**: An operational change should always have a documented undo.
