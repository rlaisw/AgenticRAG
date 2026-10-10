# Data Model: Port Alignment

**Feature**: specs/004-port-alignment/spec.md

## Entities

### PortSpec
The aligned port definition for one service.

| Field | Type | Notes |
|---|---|---|
| service | enum | `sidecar` \| `searxng` |
| port | int | The single aligned number — both the host published port and the container listen port (equal by definition) |
| env_var | string | The mechanism that sets it: `MCP_PORT` (sidecar), `GRANIAN_PORT` (searxng) |

Values after this feature:

| service | port | env_var | docker mapping |
|---|---|---|---|
| sidecar | 28080 | MCP_PORT=28080 | `-p 28080:28080` |
| searxng | 28888 | GRANIAN_PORT=28888 | `-p 28888:28888` |

### EndpointReference
Any URL or compose mapping that references a service's port.

| Field | Type | Notes |
|---|---|---|
| location | string | file:line or config key (e.g. `DEPLOY.md:Step 4`, `config.toml [web.searxng] url`) |
| old_value | string | the pre-alignment reference (e.g. `http://agentic-rag:8080/mcp`) |
| new_value | string | the post-alignment reference (e.g. `http://agentic-rag:28080/mcp`) |

Full sweep list (research.md D6): 9 locations in committed files + 1 user-level skill file.

## State Transitions

```
before:  host:28080 → container:8080 (sidecar)     | host:28888 → container:8080 (searxng)
after:   host:28080 → container:28080 (sidecar)    | host:28888 → container:28888 (searxng)

migration:
  1. stop sidecar (old port freed)
  2. recreate sidecar with aligned port (new port active)
  3. stop searxng (old port freed)
  4. recreate searxng with aligned port (new port active)
  5. update config.toml [web.searxng] url
  6. restart sidecar (pick up new searxng URL)
  7. delete Dify MCP entry → re-add with new URL
  8. verify (healthz, tools/list, web_search, ask)
  9. update all committed docs + skill
```

No intermediate state where both old and new ports are active (FR-007: clean cutover).
