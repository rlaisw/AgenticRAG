# Quickstart: Specialty Web Search Validation

**Feature**: specs/005-specialty-search/spec.md

## Prerequisites

Sidecar running (aligned port 28080), SearXNG reachable, and a `specialty_profiles.json` file created:

```bash
cat > ~/.config/agentic-rag-mcp/specialty_profiles.json <<'EOF'
{
  "microsoft": {
    "sites": ["learn.microsoft.com", "techcommunity.microsoft.com"],
    "description": "Microsoft product documentation and community"
  },
  "security": {
    "sites": ["owasp.org", "nist.gov"],
    "description": "Security standards and advisories"
  }
}
EOF
```

## S1 — `specialty_profiles()` listing (FR-009)

```bash
curl -s -m 15 http://localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"specialty_profiles","arguments":{}}}'
```

**Expected**: JSON listing both profiles with their sites and descriptions.

## S2 — `specialty_search` scoped results (FR-005/006 / SC-001)

```bash
curl -s -m 30 http://localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"specialty_search","arguments":{"query":"DKIM Exchange Online","profile":"microsoft","limit":3}}}'
```

**Expected**: Every result URL contains `learn.microsoft.com` or `techcommunity.microsoft.com` (substring match).

## S3 — Honest errors (FR-007 / SC-003)

```bash
# invalid profile
curl -s -m 15 http://localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"specialty_search","arguments":{"query":"test","profile":"nonexistent"}}}'
```

**Expected**: `{"error": "profile 'nonexistent' not found", "available": {...}}` — with both profile names and descriptions.

## S4 — Hot-reload (FR-002 / SC-002)

```bash
# add a new profile while the server is running
python3 -c "
import json
d = json.load(open('$HOME/.config/agentic-rag-mcp/specialty_profiles.json'))
d['python_dev'] = {'sites': ['docs.python.org', 'realpython.com'], 'description': 'Python docs'}
json.dump(d, open('$HOME/.config/agentic-rag-mcp/specialty_profiles.json','w'), indent=2)
"
# immediately search with it — no restart
curl -s -m 15 http://localhost:28080/mcp -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"specialty_search","arguments":{"query":"asyncio","profile":"python_dev","limit":3}}}'
```

**Expected**: the new `python_dev` profile works immediately; every URL contains `docs.python.org` or `realpython.com`.

## S5 — Contract freeze (SC-004)

```bash
.venv/bin/python -m pytest tests/ -q
```

**Expected**: all existing tests plus new specialty suites green; `web_search` canary (`test_web_providers.py`, `test_web_research_contract.py`) unchanged.

## S6 — Dify agent combined reasoning (US3 / SC-005)

Through the chatflow, ask: *"How do I configure DKIM in Exchange Online?"*

**Expected**: the agent calls both `specialty_search` (→ learn.microsoft.com) and `web_search` (→ broader results), synthesizes with the Microsoft docs as primary authority.

## Notes

- Full schema: [contracts/specialty-search-tool.md](contracts/specialty-search-tool.md)
- Profile format and normalization: [data-model.md](data-model.md)
- After implementation: refresh Dify's tool cache and re-import the chatflow DSL (12→13 tools)
