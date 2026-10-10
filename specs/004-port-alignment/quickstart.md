# Quickstart: Port Alignment Validation

**Feature**: specs/004-port-alignment/spec.md

## Prerequisites

The sidecar and SearXNG have been recreated with aligned ports (see `contracts/port-alignment.md` for the before→after table). Dify's MCP entry has been re-registered.

## S1 — Sidecar aligned port (FR-001 / SC-001)

```bash
docker port agentic-rag
# EXPECTED: 28080/tcp -> 0.0.0.0:28080   (same number in and out)

curl -s http://localhost:28080/healthz
# EXPECTED: {"status": "ok"}
```

## S2 — SearXNG aligned port (FR-002 / SC-002)

```bash
docker port searxng
# EXPECTED: 28888/tcp -> 0.0.0.0:28888   (same number in and out)

curl -s "http://localhost:28888/search?q=test&format=json" -o /dev/null -w "%{http_code}"
# EXPECTED: 200
```

## S3 — Dify MCP re-registration (FR-003 / SC-003)

```bash
# From inside the Dify network:
docker exec docker-api-1 curl -s -m 15 http://agentic-rag:28080/mcp \
  -X POST -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
# EXPECTED: 11 tools listed
```

## S4 — web_search through aligned SearXNG (FR-004 / SC-004)

```bash
docker exec docker-api-1 curl -s -m 60 http://agentic-rag:28080/mcp \
  -X POST -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"web_search","arguments":{"query":"current time Hong Kong","limit":1}}}'
# EXPECTED: at least 1 live result
```

## S5 — Clean cutover (FR-007 / SC-006)

```bash
curl -s -m 3 http://localhost:8080/healthz 2>&1 | head -1
# EXPECTED: connection refused (old port is gone)
```

## S6 — Docs alignment (FR-005 / SC-005)

```bash
grep -rn ":8080\|:8888" README.md DEPLOY.md docs/ dify/docker/
# EXPECTED: zero matches (excluding historical specs 001-003)
```

## Notes

- Full before→after reference: [contracts/port-alignment.md](contracts/port-alignment.md)
- Entities and migration sequence: [data-model.md](data-model.md)
- Rollback: revert the docker run command, revert config.toml URL, restart, delete + re-add Dify entry with old URL (~5 min)
