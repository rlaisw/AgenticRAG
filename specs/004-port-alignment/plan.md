# Implementation Plan: Port Alignment — Host Port Equals Container Port

**Branch**: `004-port-alignment` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-port-alignment/spec.md`

## Summary

Change the AgenticRAG sidecar and SearXNG containers from the "published-port ≠ internal-port" mapping (28080:8080, 28888:8080) to aligned mapping (28080:28080, 28888:28888). The host port equals the container port everywhere — no mental translation. Zero new dependencies, zero code changes; purely configuration, environment variables, Docker commands, documentation, and Dify re-registration.

## Technical Context

**Language/Version**: Python 3.12 (sidecar server.py)
**Primary Dependencies**: No changes — existing mcp SDK 1.30, httpx, bs4+lxml

**Port control mechanisms (verified in code)**:
- Sidecar: `dify/docker/mcp-server/server.py` reads `MCP_PORT` env (default `"8080"`) → change to `"28080"` via Docker `-e MCP_PORT=28080` or by changing the code default
- SearXNG: the `searxng/searxng` image honors `GRANIAN_PORT` env (currently `"8080"` hardcoded in the image) → set `-e GRANIAN_PORT=28888`

**Storage**: No changes — LanceDB, state.sqlite3, HF cache mounts all unchanged
**Testing**: No code-test changes — the 131-test suite uses in-process `call_tool`, not HTTP
**Project Type**: MCP server (stdio / stateless HTTP sidecar)
**Performance Goals**: None new — same service, same latency
**Constraints**: Tool response contracts frozen (Constitution I / FR-006); clean cutover (FR-007 — old port refused)
**Scale/Scope**: Single deployment; two containers; one Dify re-registration

## Constitution Check

| Principle | Status | Evidence |
|---|---|---|
| I. Contract Preservation | PASS | FR-006 pins all 11 tool response shapes; only the listen port changes |
| II. Tests-First | PASS (waived for this feature) | No new logic — config-only change; existing 131 tests pass unchanged; no new test file needed |
| III. Minimal Dependencies | PASS | Zero new dependencies |
| IV. Honest Answers | PASS | Clean cutover (FR-007) — old port refused, no half-state |
| V. Spec-Driven Replacement | PASS | Config replacement, not code replacement; old values deleted from all committed references (FR-005) |

## Project Structure

### Documentation (this feature)

```text
specs/004-port-alignment/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output (port-alignment contract)
├── quickstart.md        # Phase 1 output
└── checklists/requirements.md
```

### Source Code changes (configuration only)

```text
dify/docker/mcp-server/
├── server.py            # MCP_PORT default: "8080" → "28080"
├── Dockerfile           # EXPOSE 8080 → EXPOSE 28080
├── docker-compose.yml   # ports: "28080:8080" → "28080:28080"

dify/docker/
└── docker-compose.yml   # (Dify-side compose entry — same port change)

src/agentic_rag_mcp/
└── config.py            # DEFAULT_CONFIG [web.searxng] comment update (the URL itself is user config)

docs/
└── NETWORK.md           # all port references: :8080 → :28080, :8080 → :28888

README.md                # docker run example: -p 28080:8080 → -p 28080:28080
DEPLOY.md                # all port references throughout

~/.config/kilo/skills/
├── agenticrag-deploy/SKILL.md     # all port references (user-level, not committed)
└── graphify-chunk-recovery/SKILL.md  # no port refs (skip)
```

### Operational steps (not code — executed at deploy time)

```text
1. Recreate agentic-rag container with -e MCP_PORT=28080 -p 28080:28080
2. Recreate searxng container with -e GRANIAN_PORT=28888 -p 28888:28888
3. Update ~/.config/agentic-rag-mcp/config.toml [web.searxng] url → http://searxng:28888
4. Restart sidecar (pick up new searxng URL)
5. Delete Dify MCP server entry → re-add with http://agentic-rag:28080/mcp
6. Refresh Dify tool cache
7. Verify: healthz, tools/list, web_search, ask, docker port output
```

## Complexity Tracking

No violations. The only non-trivial aspect is the Dify re-registration (delete + re-add due to the edit-path bug) — documented in the spec's blast-radius header and the operational steps.
