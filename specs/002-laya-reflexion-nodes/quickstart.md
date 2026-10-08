# Quickstart: Dual-System Workflow Validation

**Feature**: specs/002-laya-reflexion-nodes/spec.md

Runnable end-to-end validation for the replaced two-system workflow. Prerequisites: project venv activated, decision-model checkpoint downloaded (first run with `[decider] enabled = true` fetches ~1.7 GB to the HF cache), fixtures ingested (existing setup).

## S1 — System 1: one-pass structured routing (US1, SC-001/002/003)

```bash
.venv/bin/python -c "
from agentic_rag_mcp.config import load_config
from agentic_rag_mcp.server import build_server
srv = build_server(load_config())
import asyncio
ans = asyncio.run(srv._call_tool_forgenerated('ask', {'question': 'What was the quarterly revenue?'}))" 2>/dev/null || true
# Simpler: run the server and call the tool over MCP:
.venv/bin/python -m agentic_rag_mcp --transport streamable-http &  # port from config
curl -s localhost:8811/mcp -X POST -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ask","arguments":{"question":"What was the quarterly revenue?"}}}'
```

**Expected**: response contains `decision` with `route: "direct_retrieval"`, `complexity` in 1–3, `sufficient: true`, `provenance: "decision_node"`, `latency_ms` below the configured `[decider] timeout` (measured ~7 s warm on a small ARM CPU; ~140 ms on Apple Silicon — SC-001's 2 s target assumes faster hardware, see plan report); `iterations: 0`; answer cites `results.pptx`. Repeat over ≥ 100 mixed questions via the test suite (below) for the SC-001/002 percentages.

## S2 — System 2: reflexion with full-history conditioning (US2, SC-004/005)

Ask a multi-part question with deliberately incomplete first-pass evidence:

```bash
curl -s localhost:8811/mcp -X POST -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"ask","arguments":{"question":"Compare the Apollo moon landing and quarterly revenue growth numbers"}}}'
```

**Expected**: `decision.route: "deliberative_reasoning"`; `reflections` is a list of structured records each with `evaluator_score` (1–10) + `evaluator_verdict` + verbal `critique` + `missing_focus`; every trial n>1's `trace` queries include the union of prior `missing_focus` terms; final answer covers both parts with citations; on budget exhaustion `confidence: "low"` and the full `reflections` list is present.

## S3 — Fallback with provenance (US3/FR-003, SC-006)

```bash
# temporarily disable the decider (simulates outage)
sed -i 's/^enabled = true/enabled = false/' ~/.config/agentic-rag-mcp/config.toml
# restart the server, re-run the S1 curl
sed -i 's/^enabled = false/enabled = true/' ~/.config/agentic-rag-mcp/config.toml  # restore
```

**Expected**: answer still arrives; `decision.provenance: "fallback"`; latency ≤ ~125% of the S1 path; after restore, the next request shows `provenance: "decision_node"` again.

## S4 — Contract preservation (FR-015, SC-007) + full suite

```bash
.venv/bin/python -m pytest tests/ -q
```

**Expected**: all pre-existing contract and integration tests pass unchanged (backward compatibility), plus the new unit/integration suites for decision-schema validation, evaluator verdicts, memory union-conditioning, and fallback provenance.

## Notes

- Full field definitions: [contracts/ask-response.md](contracts/ask-response.md) and [contracts/decision-schema.md](contracts/decision-schema.md); entities: [data-model.md](data-model.md).
- The 100-question SC-001/002/003 measurement runs as part of the integration suite, not by hand.
- Do not run this quickstart against the production Dify sidecar while `[decider]` is being toggled — use the host venv server.
