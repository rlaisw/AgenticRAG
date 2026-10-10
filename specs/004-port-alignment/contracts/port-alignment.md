# Contract: Port Alignment

**Feature**: specs/004-port-alignment/spec.md | FR-001..FR-007

The MCP tool contracts are UNCHANGED (Constitution I / FR-006). This contract covers only what changes: the listen ports and endpoint references.

## Before → After

| Reference | Before | After |
|---|---|---|
| Sidecar container listen port | 8080 | **28080** |
| Sidecar host publish | 28080 | **28080** (unchanged) |
| Docker mapping | `-p 28080:8080` | **`-p 28080:28080`** |
| `docker port` output | `8080/tcp -> 0.0.0.0:28080` | **`28080/tcp -> 0.0.0.0:28080`** |
| Dify UI URL | `http://agentic-rag:8080/mcp` | **`http://agentic-rag:28080/mcp`** |
| SearXNG container listen port | 8080 | **28888** |
| SearXNG host publish | 28888 | **28888** (unchanged) |
| SearXNG Docker mapping | `-p 28888:8080` | **`-p 28888:28888`** |
| `[web.searxng] url` in config.toml | `http://searxng:8080` | **`http://searxng:28888`** |
| Host healthz check | `curl localhost:28080/healthz` | unchanged |
| Host SearXNG JSON check | `curl localhost:28888/...` | unchanged |

## What does NOT change

| Item | Status |
|---|---|
| All 11 MCP tool response shapes | **frozen** (Constitution I) |
| SSRF allowlist (`SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=agentic-rag`) | unchanged (domain-based) |
| Chatflow DSL tool entries (`provider_name: agentic-rag`) | unchanged (identifier-based) |
| Volumes (config, HF cache, fixtures) | unchanged |
| Docker networks (docker_default, docker_ssrf_proxy_network) | unchanged |
| scripts/run_http.py (8811), run_sse.py (8812) | unchanged (dev transports) |
| 131-test suite | unchanged (in-process, no HTTP) |

## Invariants

1. **Aligned** (FR-001/002): `docker port <container>` shows `PORT/tcp -> 0.0.0.0:PORT` — same number in and out.
2. **Contracts frozen** (FR-006): all 11 tools return the same schemas through the new port.
3. **Clean cutover** (FR-007): `localhost:8080` returns connection refused after migration.
4. **Docs aligned** (FR-005 / SC-005): `grep -rn ":8080\|:8888" README.md DEPLOY.md docs/ dify/docker/` → zero matches.
5. **Dify re-registered** (FR-003): the MCP server is reachable at `http://agentic-rag:28080/mcp` from Dify containers.
6. **SearXNG functional** (FR-004 / SC-004): `web_search` returns live results through the aligned SearXNG port.
