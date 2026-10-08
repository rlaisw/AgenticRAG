# Contract: System 1 Decision Schema

**Feature**: specs/002-laya-reflexion-nodes/spec.md | FR-001, FR-002, FR-004

The embedded decision node exposes one operation — `decide(question) -> DecisionResult` — internally backed by the Laya decision model's `system_one` API (one forward pass, three typed questions). No text is ever generated or returned by the decider.

## Request (internal)

The question text is passed as the decision state; the three primitives are asked in a single batched pass:

| Primitive | Question | Type |
|---|---|---|
| `choice` | "Which route should handle this request?" over `route_options` with per-option criteria | one of the 4 fixed options |
| `score` | "How complex is this request?" over the 10-level rubric | integer 1–10 (rounded expected level) |
| `noul` | "The knowledge base alone is likely sufficient to answer this request." | P(true) ≥ `noul_threshold` → true |

## Response: DecisionResult

```json
{
  "route": "direct_retrieval",
  "complexity": 2,
  "sufficient": true,
  "route_probabilities": {"direct_retrieval": 0.91, "deliberative_reasoning": 0.05, "live_web": 0.03, "source_management": 0.01},
  "provenance": "decision_node",
  "latency_ms": 142,
  "valid": true
}
```

## Validation rules (FR-004 — failure of any rule = decider unavailable → fallback)

1. `route` MUST be one of the four `route_options` — otherwise invalid.
2. `complexity` MUST be an integer in [1, 10] — otherwise invalid.
3. `provenance` MUST be `decision_node` when the decider produced the result; `fallback` results are constructed by the fallback router, never by the decider.
4. Timeout: if the pass exceeds `[decider] timeout` (default 3.0 s), the attempt is invalid → fallback.
5. Model-not-loaded, load-failure, or malformed model output → invalid → fallback.

## Provenance guarantee (FR-003, SC-003)

With the decider operational, 100% of primary-path responses carry `provenance: "decision_node"`. The keyword heuristic runs ONLY when the decider is invalid/unavailable, and those responses carry `provenance: "fallback"` and are marked fallback-served. There is no third provenance value.
