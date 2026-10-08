# Contract: `ask` Tool Response (preserved + extended)

**Feature**: specs/002-laya-reflexion-nodes/spec.md | FR-005, FR-008, FR-011, FR-014, FR-015

The `ask` MCP tool's client-facing response is PRESERVED field-for-field (FR-015 / SC-007); this feature adds two fields and enriches one existing field. The Dify chatflow and the existing contract test suite must behave identically for all pre-existing fields.

## Preserved fields (unchanged semantics)

| Field | Type | Notes |
|---|---|---|
| answer | string | synthesized answer text |
| confidence | enum | `normal` \| `low` — low when budget exhausted or fallback-served with no evidence |
| classification | string | route label as today (`fast` / `deliberative`) — derived from `decision.route` |
| iterations | int | reflexion trials run (direct path: 0) |
| sufficiency | enum | `satisfied` \| `exhausted` |
| trace | list[object] | per-tool retrieval records |
| citations | list[object] | cited sources |
| error | object \| null | e.g., SufficiencyExhausted payload |
| plan | list[object] | final sub-task plan |

## New fields

| Field | Type | Notes |
|---|---|---|
| decision | DecisionResult | the System 1 verdict incl. `provenance` and `latency_ms` (see decision-schema.md) |
| reflections | list[ReflectionRecord] | REPLACES the interim critique strings with structured records (same field name, richer content — FR-008/FR-009) |

## Invariants

1. **Route mapping (FR-005)**: `route ∈ {direct_retrieval, source_management}` → direct path, zero iterations; `route ∈ {deliberative_reasoning, live_web}` → reflexion loop; `live_web` orders web tools first in trial 1. `source_management` questions receive routing guidance in `answer`, never performed operations.
2. **Evaluator gating (FR-007/FR-010)**: the loop retries ONLY on `evaluator_verdict == "fail"`; every record carries both `evaluator_score` (1–10) and the verdict; a passed draft is final.
3. **Memory conditioning (FR-009)**: for every trial n > 1, that trial's queries include the union of `missing_focus` terms from reflections 1..n−1.
4. **Budget (FR-011 / SC-005)**: no request exceeds `max_iterations`; exhausted responses carry `confidence: "low"` and the full `reflections` list.
5. **Fallback marking (FR-003/FR-007)**: when `decision.provenance == "fallback"`, the response is fallback-served and marked as such; direct-path and loop behavior otherwise unchanged.
6. **Traceability (FR-014)**: `decision` + `reflections` are present on every response, both provenances.

## Backward-compatibility acceptance

The pre-existing contract test suite (`tests/contract/`, plus the deep-path integration assertions) must pass unchanged against the replaced implementation — every field above with "preserved" semantics is asserted there today.
