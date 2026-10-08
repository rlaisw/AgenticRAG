# Data Model: Dual-System Workflow — Structured Decider + Reflexion Loop

**Feature**: specs/002-laya-reflexion-nodes/spec.md

## Entities

### DecisionSchema
Versioned definition of the System 1 decision point. One instance, versioned with the workflow.

| Field | Type | Notes |
|---|---|---|
| version | string | schema version, bumped on any option/scale change |
| route_options | list[string] | exactly: `direct_retrieval`, `deliberative_reasoning`, `live_web`, `source_management` |
| route_criteria | map[string, string] | per-option decision guidance supplied to the choice primitive |
| complexity_levels | list[string] | 10 ordered rubric levels (1–10); bands: 1–3 simple, 4–7 moderate, 8–10 complex |
| sufficiency_question | string | the `noul` yes/no statement ("the knowledge base alone is likely sufficient") |
| noul_threshold | float | default 0.5; P(true) ≥ threshold → `true` |

Validation rules (FR-002/FR-004): every decision output is checked against this schema; an out-of-set route, non-integer or out-of-range score, or malformed response is rejected → decider treated as unavailable → fallback routing with provenance marking.

### DecisionResult
Output of the System 1 node for one request.

| Field | Type | Notes |
|---|---|---|
| route | enum(route_options) | selected route (argmax of calibrated choice probabilities) |
| complexity | int (1–10) | rounded expected level of the score primitive; banded per DecisionSchema |
| sufficient | bool | derived: route == direct_retrieval (T031 calibration; noul asked for schema fidelity) |
| route_probabilities | map[string, float] | calibrated probabilities per route option (observability) |
| provenance | enum | `decision_node` \| `fallback` |
| latency_ms | int | decision wall time (SC-001 measurement) |
| valid | bool | false when output failed schema validation (→ fallback consumed) |

### ReflectionRecord
One reflexion cycle's outcome, produced by the Self-Reflector stage.

| Field | Type | Notes |
|---|---|---|
| iteration | int | 1-based trial number |
| evaluator_score | int (1–10) | rule-based quality score of the draft |
| evaluator_verdict | enum | `pass` \| `fail` |
| critique | string | verbal critique describing the specific failure (not a bare keyword list) |
| missing_focus | list[string] | concrete shortfalls (e.g., uncovered question terms) to target next trial |

### EpisodicMemory
Per-request ordered buffer of ReflectionRecords. Lifecycle: created empty at request start; appended by the Self-Reflector stage; read by the Actor stage to condition each subsequent trial's queries on the UNION of all `missing_focus` terms; discarded when the request completes (FR-012 — no persistence, no cross-request leakage, no growth cap needed because trial count is bounded by `max_iterations`).

## State Transitions (request lifecycle)

```
request received
  → DECIDE (System 1: one pass, three primitives)
      ├─ valid   → route per FR-005 mapping:
      │    ├─ direct_retrieval | source_management → DIRECT (single retrieval; guidance for source route)
      │    └─ deliberative_reasoning | live_web     → REFLEXION (web tools first when live_web)
      └─ invalid/timeout/unloaded → FALLBACK heuristic route (provenance: fallback)
  → REFLEXION loop (System 2, bounded by max_iterations):
        ACTOR (retrieve + draft, conditioned by episodic memory union-terms)
        → EVALUATOR (score + verdict; sufficiency hits are an input)
        → pass    → END (answer, confidence: normal, reflections emitted)
        → fail    → SELF-REFLECTOR (verbal critique, missing_focus)
                  → MEMORY (append record)
                  → ACTOR …  (or END on budget exhaustion: confidence: low, error: SufficiencyExhausted)
  → RESPONSE (all fields of the preserved contract + decision + reflections)
```

Invariants: a passed draft is never re-evaluated; every trial after the first is conditioned on the full memory union; budget-exhausted responses carry `confidence: low` and the full memory (FR-011, SC-005).

## Configuration additions (`config.toml`)

```toml
[decider]
enabled = true            # false → heuristic fallback is primary (provenance: fallback)
model_repo = "convaiinnovations/laya"
model_dir = ""             # optional local checkpoint dir (overrides download)
timeout = 12.0              # seconds; exceeded → fallback (T030 reconciliation: measured
                            # ~7.4s warm torch inference on the ARM reference host;
                            # the original 3.0 draft predated the hardware measurement)
noul_threshold = 0.5
```

`[laya]` section (external app URL/token) is removed along with `routing/laya.py` (FR-013).

## Response trace additions (see contracts/ask-response.md)

- `decision`: the DecisionResult object
- `reflections`: list of ReflectionRecords (replaces the interim critique list; same field name, richer records)
