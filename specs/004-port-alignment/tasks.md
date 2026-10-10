---
description: "Task list for feature implementation"
---

# Tasks: Port Alignment — Host Port Equals Container Port

**Input**: Design documents from `specs/004-port-alignment/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/port-alignment.md, quickstart.md

**Tests**: NONE — this is a configuration-only change. The existing 131-test suite uses in-process `call_tool` and is unaffected by port changes. No new tests required (plan.md Constitution Check, waived per Principle II for config-only).

**Organization**: Tasks grouped by user story. This is a short list — the feature is pure config/docs with no code to write.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (No story label — shared config)

**Purpose**: Update the container code and Docker config files that define the listen ports

- [X] T001 Change the default `MCP_PORT` from `"8080"` to `"28080"` in dify/docker/mcp-server/server.py (line 18: `os.environ.get("MCP_PORT", "8080")` → `"28080"`) and update the docstring references from `:8080` to `:28080`
- [X] T002 [P] Change `EXPOSE 8080` to `EXPOSE 28080` in dify/docker/mcp-server/Dockerfile
- [X] T003 [P] Change the ports line from `"28080:8080"` to `"28080:28080"` in dify/docker/mcp-server/docker-compose.yml

---

## Phase 2: User Story 1 — Aligned Sidecar Port (Priority: P1) 🎯 MVP

**Goal**: The sidecar container listens on 28080 internally; `-p 28080:28080` produces a single aligned port number

**Independent Test**: `docker port agentic-rag` shows `28080/tcp -> 0.0.0.0:28080`; `curl localhost:28080/healthz` returns `{"status": "ok"}`; from Dify, `curl http://agentic-rag:28080/mcp` completes the MCP handshake (quickstart.md S1, S3)

### Implementation for User Story 1

- [X] T004 [US1] Rebuild the sidecar image and recreate the container with the aligned port: `docker build -f dify/docker/mcp-server/Dockerfile -t agentic-rag-mcp:latest .` then `docker rm -f agentic-rag && docker run -d --name agentic-rag --network docker_default --network docker_ssrf_proxy_network -v ~/.config/agentic-rag-mcp:/root/.config/agentic-rag-mcp -v ~/.cache/huggingface:/root/.cache/huggingface -v /home/ubuntu/kilocode/AgenticRAG/specs/001-agentic-rag-mcp/fixtures:/data/fixtures -p 28080:28080 --restart always agentic-rag-mcp:latest` (verify: `docker port agentic-rag` shows aligned port; healthz on 28080)
- [X] T005 [US1] Delete the existing "Agentic RAG" MCP server entry in Dify and re-add with `http://agentic-rag:28080/mcp` (no headers, no DCR, identifier `agentic-rag`) — then refresh the Dify tool cache (10–11 tools must appear) and verify `tools/list` from the Dify network returns the full toolset

**Checkpoint**: Sidecar aligned and Dify re-registered — the chatflow works through the new port

---

## Phase 3: User Story 2 — Aligned SearXNG Port (Priority: P2)

**Goal**: The SearXNG container listens on 28888 internally; `-p 28888:28888` produces the same alignment; AgenticRAG's config points at the new port

**Independent Test**: `docker port searxng` shows `28888/tcp -> 0.0.0.0:28888`; `curl localhost:28888/search?q=test&format=json` returns 200; `web_search` through the MCP tool returns live results (quickstart.md S2, S4)

### Implementation for User Story 2

- [X] T006 [US2] Recreate the SearXNG container with the aligned port: `docker rm -f searxng && docker run -d --name searxng -v /home/ubuntu/searxng:/etc/searxng -e GRANIAN_PORT=28888 -p 28888:28888 --restart unless-stopped searxng/searxng && docker network connect docker_default searxng && docker network connect docker_ssrf_proxy_network searxng` (verify: JSON API on 28888 returns 200)
- [X] T007 [US2] Update `~/.config/agentic-rag-mcp/config.toml` `[web.searxng] url` from `http://searxng:8080` to `http://searxng:28888` and restart the sidecar container (`docker restart agentic-rag`) to pick it up

**Checkpoint**: SearXNG aligned; web_search verified through the new port

---

## Phase 4: User Story 3 — Documentation & Skill Alignment (Priority: P1)

**Goal**: Every committed reference uses the aligned port scheme; `grep :8080` on operational docs returns zero

**Independent Test**: `grep -rn ":8080\|:8888" README.md DEPLOY.md docs/ dify/docker/` returns zero matches (quickstart.md S6)

### Implementation for User Story 3

- [X] T008 [P] [US3] Update all port references in README.md: `-p 28080:8080` → `-p 28080:28080`, the `[web.searxng]` comment `:8080` → `:28888`, and any remaining `:8080` or `:8888` mentions
- [X] T009 [P] [US3] Update all port references in DEPLOY.md: Step 3 docker run `-p 28080:8080` → `-p 28080:28080`, Step 4 Dify URL `http://agentic-rag:8080/mcp` → `http://agentic-rag:28080/mcp`, Step 5 SearXNG `-p 28888:8080` → `-p 28888:28888` + `[web.searxng] url` → `http://searxng:28888`, port convention card, troubleshooting table
- [X] T010 [P] [US3] Update all port references in docs/NETWORK.md: mermaid diagram (`:8080` → `:28080` for agentic-rag, `:8080` → `:28888` for searxng), connection matrix (rows ③–⑥), port reference card, troubleshooting table
- [X] T011 [P] [US3] Update the agenticrag-deploy skill at ~/.config/kilo/skills/agenticrag-deploy/SKILL.md: port convention, Step 3 docker run, Step 4 Dify URL, Step 5 SearXNG command + verify URL, troubleshooting table
- [X] T012 [US3] Verify: `grep -rn ":8080\|:8888" README.md DEPLOY.md docs/ dify/docker/` returns zero matches (SC-005)

**Checkpoint**: Docs fully aligned; grep clean

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T013 Verify clean cutover: `curl -s -m 3 http://localhost:8080/healthz` returns connection refused (FR-007 / SC-006); confirm no container listens on 8080 (`docker ps` port mappings)
- [X] T014 Run the full 131-test suite to confirm no regression (should pass unchanged — ports are deployment-only)
- [ ] T015 Commit all changes and push to GitHub

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001–T003; T002+T003 parallel after T001
- **US1 (Phase 2)**: depends on T001 (the code change); T004 → T005 sequential (must rebuild before re-registering Dify)
- **US2 (Phase 3)**: independent of US1 — can run in parallel; T006 → T007 sequential
- **US3 (Phase 4)**: T008–T011 all parallel (different files); T012 verify after all
- **Polish (Phase 5)**: after all stories

### Within Each User Story

- Container recreation before Dify/config changes (new port must be live before re-registering)
- US3 doc updates can proceed while US1/US2 are deploying (they describe the end state)

### Parallel Opportunities

- T002 + T003 (different files)
- T004 (sidecar) + T006 (SearXNG) — different containers, independent
- T008 + T009 + T010 + T011 — four different doc files

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (T001–T003) → code + Docker config updated
2. Phase 2 (T004–T005) → sidecar live on aligned port, Dify re-registered
3. **STOP and VALIDATE**: quickstart.md S1 + S3 + S5 (aligned port, Dify handshake, old port refused)

### Incremental Delivery

1. Setup → aligned code/config
2. + US1 → MVP (sidecar aligned, Dify working)
3. + US2 → SearXNG aligned, web_search verified
4. + US3 → docs/skill fully aligned, grep clean
5. Polish → cutover check, suite green, commit + push

---

## Notes

- [P] tasks = different files, no dependencies
- This is a SHORT list (15 tasks) — the feature is purely configuration, Docker commands, and documentation
- The most critical single step is **T005** (Dify re-registration) — missing it breaks the chatflow
- Rollback: revert docker run command, revert config.toml, restart, delete + re-add Dify entry with old URL (~5 min)
