---
description: "Task list for feature implementation"
---

# Tasks: Dual-System Workflow — Structured Decider + Reflexion Loop

**Input**: Design documents from `specs/002-laya-reflexion-nodes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/decision-schema.md, contracts/ask-response.md

**Tests**: Included — repo convention is tests-first (per plan.md Constitution Check). Write test tasks RED before their implementation tasks.

**Organization**: Tasks grouped by user story; each story is independently testable (US2 drives the reflexion graph via `mode: "deep"` so it does not depend on US1's decider).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project: `src/`, `tests/` at repository root (package `agentic_rag_mcp`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Config surface, decision-model runtime, and shared entities

- [X] T001 [P] Add `[decider]` section to `src/agentic_rag_mcp/config.py`: `enabled = true`, `model_repo = "convaiinnovations/laya"`, `model_dir = ""`, `timeout = 3.0`, `noul_threshold = 0.5` (values per data-model.md Configuration additions; keep `[laya]` section until T011)
- [X] T002 [P] Create the Laya decision-model runtime `src/agentic_rag_mcp/routing/laya_runtime.py`: lazy-load the checkpoint (HF download to cache, `model_dir` override) and expose a `system_one(state, questions)` adapter returning the three primitives (choice probabilities / score expected-level / noul P(true)); per research.md D2
- [X] T003 [P] Create shared entities `src/agentic_rag_mcp/agents/memory.py`: `ReflectionRecord(iteration, evaluator_score, evaluator_verdict, critique, missing_focus)` and `EpisodicMemory` (ordered per-request buffer; lifecycle per data-model.md — created empty at request start, discarded at completion, no persistence)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Decision schema + validation that every story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Write failing unit tests `tests/unit/test_decision_schema.py`: route outside `{direct_retrieval, deliberative_reasoning, live_web, source_management}` → invalid; complexity outside integer 1–10 → invalid; noul P(true) ≥ `noul_threshold` (default 0.5) → sufficient true; provenance only `decision_node|fallback` (FR-002/FR-004, contracts/decision-schema.md)
- [X] T005 Make T004 pass: implement `DecisionSchema` + `DecisionResult` + `validate()` in `src/agentic_rag_mcp/routing/decision.py` (schema: version, 4 route options with criteria, 10-level rubric with bands 1–3 simple / 4–7 moderate / 8–10 complex, sufficiency noul question, noul_threshold; result: route, complexity, sufficient, route_probabilities, provenance, latency_ms, valid)
- [X] T006 [P] Write failing unit tests `tests/unit/test_memory.py`: memory starts empty per request; append ordering; union of all `missing_focus` across records (FR-009 full-history conditioning); no cross-request leakage (FR-012)
- [X] T007 Make T006 pass: implement union-conditioning helper and per-request lifecycle semantics in `src/agentic_rag_mcp/agents/memory.py`

**Checkpoint**: Foundation ready — user story implementation can begin in parallel

---

## Phase 3: User Story 1 — One-Pass Structured Routing (Priority: P1) 🎯 MVP

**Goal**: Every `ask` request is routed by the embedded decision node in one pass (choice + score + boolean), direct routes answered in a single retrieval step, decision-service provenance recorded

**Independent Test**: Submit "What was the quarterly revenue?" with `[decider] enabled = true`; response `decision` shows `route: "direct_retrieval"`, `complexity` 1–3, `sufficient: true`, `provenance: "decision_node"`, `iterations: 0`, answer cites `results.pptx` (quickstart.md S1)

### Tests for User Story 1

- [X] T008 [P] [US1] Write failing integration tests `tests/integration/test_decision_routing.py`: direct-route question → `provenance: "decision_node"`, `iterations: 0`, citations present; no free text or out-of-set route anywhere in the decision object (quickstart.md S1)
- [X] T009 [P] [US1] Write failing unit tests `tests/unit/test_decider_engine.py` with the model mocked: valid three-primitive output maps to DecisionResult (argmax route, rounded+banded score, thresholded noul); timeout beyond `[decider] timeout` → `valid: false`; malformed output → `valid: false` (contracts/decision-schema.md validation rules 1–5)

### Implementation for User Story 1

- [X] T010 [US1] Implement the decider engine `decide(question)` in `src/agentic_rag_mcp/routing/decision.py`: one `system_one` pass via `laya_runtime` with the DecisionSchema questions; map choice/score/noul to DecisionResult; enforce timeout; on any validation failure return the invalid result (fallback consumed at the call site) (FR-001, FR-002)
- [X] T011 [US1] Wire `src/agentic_rag_mcp/server.py` ask flow to the decider as primary router with FR-005 route mapping: `direct_retrieval` and `source_management` → direct single-retrieval path (source-management questions answer with routing guidance, never performing source operations); `deliberative_reasoning` and `live_web` → deliberation path; move `heuristic_classify` from `src/agentic_rag_mcp/routing/laya.py` into `src/agentic_rag_mcp/routing/fallback.py`, then DELETE `src/agentic_rag_mcp/routing/laya.py` and the `[laya]` config section (FR-013 part 1)
- [X] T012 [US1] Add the `decision` object (full DecisionResult incl. `provenance`, `latency_ms`) to every `ask` response in `src/agentic_rag_mcp/server.py`; derive `classification` from `decision.route`; keep every preserved field from contracts/ask-response.md untouched (FR-014, FR-015)

**Checkpoint**: US1 fully functional — decider is primary, provenance visible, old client removed

---

## Phase 4: User Story 2 — Reflexion Cycle with Discrete Stages (Priority: P2)

**Goal**: Complex routes run the LangGraph reflexion graph — Actor → Evaluator (score + verdict) → Self-Reflector → Episodic Memory — with full-history conditioning and bounded retries

**Independent Test**: Ask "Compare the Apollo moon landing and quarterly revenue growth numbers" with `mode: "deep"`; response `reflections` contains structured records (score, verdict, verbal critique, missing_focus), trials after the first carry union-conditioned queries, final answer covers both parts (quickstart.md S2)

### Tests for User Story 2

- [X] T013 [P] [US2] Write failing unit tests `tests/unit/test_evaluator.py`: deterministic score 1–10 from coverage + citability (+ sufficiency hits as input); pass requires coverage threshold AND citable evidence; identical inputs → identical outputs (FR-007, FR-010)
- [X] T014 [P] [US2] Write failing unit tests `tests/unit/test_reflexion_graph.py` with fake tools: fail → Self-Reflector verbal critique → memory append → retry with union terms; pass → END with no further Actor run; budget exhaustion → confidence "low" + full reflections + SufficiencyExhausted error (FR-006, FR-008, FR-009, FR-011)
- [X] T015 [P] [US2] Write failing integration tests `tests/integration/test_reflexion_conditioning.py`: three-part question where trial 1 covers one part — trial 2 targets the rest; a part fixed in trial 1 does not regress in trial 3 (union conditioning, no-regression); `live_web` route orders web tools first in trial 1 (US2 AC1/AC2, FR-005)

### Implementation for User Story 2

- [X] T016 [US2] Implement the rule-based Evaluator in `src/agentic_rag_mcp/agents/evaluator.py`: score = 10 × coverage halved when no citable evidence, verdict = pass iff coverage ≥ threshold AND citable evidence present; the legacy hit-count check (`agents/sufficiency.py`) becomes an input signal only (research.md D5, FR-010)
- [X] T017 [US2] Implement the reflexion graph in `src/agentic_rag_mcp/agents/reflexion.py` as a LangGraph `StateGraph`: nodes Actor (retrieve + draft, queries conditioned on the memory union terms), Evaluator (T016), Self-Reflector (verbal critique naming the specific failure + missing_focus extraction), Episodic Memory (append record); conditional edge retries only on fail verdict, END on pass or exhausted budget (research.md D3/D6)
- [X] T018 [US2] Wire `src/agentic_rag_mcp/server.py`: `deliberative_reasoning` and `live_web` routes invoke the reflexion graph; emit `reflections` as structured ReflectionRecords; DELETE `src/agentic_rag_mcp/agents/graph.py` and its imports (FR-013 part 2)
- [X] T019 [US2] Update the existing reflexion tests (`tests/unit/test_reflexion.py`, deep-path integration assertions in `tests/integration/test_end_to_end.py`) to the new graph without weakening their contracts (FR-015 / SC-007)

**Checkpoint**: US1 and US2 both work independently; monolithic loop is gone

---

## Phase 5: User Story 3 — Decision Resilience, Provenance, Traceability (Priority: P3)

**Goal**: Decider outage degrades to marked fallback without dead-ending requests; full decision + reflection trace on every response; old design fully unreachable

**Independent Test**: Set `[decider] enabled = false`, ask any question → answer arrives with `provenance: "fallback"`; re-enable → next response shows `provenance: "decision_node"`; run the full pytest suite → all pre-existing contract tests pass unchanged (quickstart.md S3/S4)

### Tests for User Story 3

- [X] T020 [P] [US3] Write failing integration tests `tests/integration/test_fallback_provenance.py`: decider disabled / timeout / invalid output → heuristic fallback routes the request, response marked `provenance: "fallback"`; recovery on the next request after re-enable; fallback latency ≤ ~125% of primary (US3 AC1/AC2, SC-006)
- [X] T021 [P] [US3] Extend contract tests `tests/contract/` to assert every preserved field from contracts/ask-response.md is present under BOTH provenance values, plus the two new fields (`decision`, `reflections`) and their invariants (FR-015, SC-007)

### Implementation for User Story 3

- [X] T022 [US3] Finalize fallback semantics in `src/agentic_rag_mcp/routing/decision.py` + `src/agentic_rag_mcp/routing/fallback.py`: every invalid/timeout/unloaded decider outcome routes via the heuristic with `provenance: "fallback"`; no third provenance value exists (FR-003, FR-007)
- [X] T023 [US3] Ensure trace completeness in `src/agentic_rag_mcp/server.py`: every response carries `decision` (with provenance and latency) and `reflections`; deliberative responses carry per-iteration evaluator scores, verdicts, critiques, and the memory contents used by each trial (FR-014)
- [X] T024 [US3] Add the SC-measurement suite `tests/integration/test_success_criteria.py`: 100-question set asserting SC-001 (95% decisions < 2 s), SC-002 (100% valid schema), SC-003 (100% decision-node provenance when enabled), SC-005 (100% budget-exhausted flagged low)
- [X] T025 [US3] Old-design retirement sweep (FR-013): grep the package for `LayaDecisionLayer`, `ReflectionAgent`, single-label `classify` calls, and `[laya]` config references; remove all remaining references and dead paths; `agents/sufficiency.py` referenced only as evaluator input

**Checkpoint**: All stories independently functional; replacement complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, deployment, and full-suite validation

- [X] T026 [P] Document the `[decider]` config section, decision-model download/cache behavior (~1.7 GB first run, ~2 GB RAM loaded), and provenance semantics in `README.md`
- [X] T027 Run the quickstart.md S1–S4 validation end-to-end against the host-venv server; record results
- [X] T028 Rebuild the Dify sidecar image (`docker build -f dify/docker/mcp-server/Dockerfile`) and refresh Dify's MCP provider tool cache so the deployed chatflow uses the replaced workflow
- [X] T029 Full suite green: `.venv/bin/python -m pytest tests/ -q` — all pre-existing 51 tests plus the new suites pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001–T003 run in parallel
- **Foundational (Phase 2)**: Depends on Phase 1 (T003) — BLOCKS all user stories
- **User Stories (Phases 3–5)**: All depend on Phase 2; then parallelizable (US2 tests drive the graph via `mode: "deep"`, so US2 does not depend on US1's decider)
- **Polish (Phase 6)**: After all desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no story dependencies (MVP)
- **US2 (P2)**: After Phase 2 — independent of US1 (integration forces `mode: "deep"`); integrates cleanly once US1 lands
- **US3 (P3)**: After Phase 2 — validates against US1's provenance types; independent test via config toggle

### Within Each User Story

- Tests written and RED before implementation tasks
- Engine/schema before wiring; wiring before response-shape changes
- Deletions (FR-013) happen with the story that replaces the component (laya.py in US1, graph.py in US2, retirement sweep in US3)

### Parallel Opportunities

- T001, T002, T003 (different files)
- T004, T006 (different test files); then T005, T007
- Within US1: T008 + T009; within US2: T013 + T014 + T015; within US3: T020 + T021
- Across stories: US2 and US3 test tasks can proceed while US1 implementation is under way

---

## Parallel Example: User Story 2

```bash
# Launch all US2 test tasks together (different files, no deps):
Task: "Write failing unit tests tests/unit/test_evaluator.py"
Task: "Write failing unit tests tests/unit/test_reflexion_graph.py"
Task: "Write failing integration tests tests/integration/test_reflexion_conditioning.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 (Foundational)
2. Complete Phase 3 (US1) — decider is primary with provenance
3. **STOP and VALIDATE**: quickstart.md S1 + S3 (config toggle) + `pytest tests/ -q`
4. Deploy/demo if ready — routing quality improves immediately even with the interim deliberation loop

### Incremental Delivery

1. Setup + Foundational → shared schema/entities ready
2. + US1 → MVP (structured routing, provenance)
3. + US2 → reflexion graph replaces the loop (quality lift on compound questions)
4. + US3 → resilience guarantees + SC measurements + retirement sweep
5. Polish → docs, sidecar rebuild, full suite

---

## Notes

- [P] tasks = different files, no dependencies
- Every task names exact file paths; constraints (route options, 1–10 bands, thresholds, timeouts) are quoted from data-model.md / contracts/ and must not be re-decided at implementation time
- Deletion tasks are explicit — old components are removed, not deprecated (FR-013)
- Commit after each task or logical group; stop at any checkpoint to validate the story independently

---

## Phase 7: Convergence

**Purpose**: Close gaps found by /speckit.converge (2026-10-08) between the implemented code and the feature artifacts. Findings F1-F6; severity-ordered.

- [X] T030 Implement the ONNX decision-model variant (receptron/laya-onnx bundle + `onnxruntime`) behind a `[decider] runtime = "torch"|"onnx"` config switch in src/agentic_rag_mcp/routing/laya_runtime.py, and measure warm decision latency on the reference host against SC-001's 2s target — OR run /speckit.clarify to amend SC-001 to hardware-relative wording per FR-001 (partial)
- [X] T031 Calibrate the System 1 sufficiency judgment so simple indexed-content questions yield sufficient=true (live model returns sufficient=False for "What is the speed of light?"): tune the noul statement in src/agentic_rag_mcp/routing/decision.py and/or `[decider] noul_threshold`, then re-validate the five live route questions per US1/AC1 (partial)
- [X] T032 Align the evaluator pass gate with SC-004's 80% multi-part coverage target: raise MIN_COVERAGE from 0.6 to 0.8 in src/agentic_rag_mcp/agents/evaluator.py (and update tests/unit/test_evaluator.py), or add a multi-part question-set measurement to tests/integration/test_success_criteria.py asserting >=80% part coverage per SC-004 (partial)
- [X] T033 Trace the post-task hardening into the spec or revert it: score-gated source_management misroute safety (src/agentic_rag_mcp/server.py, Lance distance <= 1.0) and route-criteria rewording (src/agentic_rag_mcp/routing/decision.py) — run /speckit.clarify to amend FR-005/US1-AC5 wording to cover misroute safety, or restore guidance-only behavior (unrequested)
- [X] T034 Add the SC-006 comparative latency assertion to tests/integration/test_fallback_provenance.py: median fallback-path ask latency <= 1.25x the primary-path latency over the same question set (replacing the current generous 10s bound) (partial)
- [X] T035 Reconcile the `[decider] timeout` default: code and README say 12.0 (measured ~7.4s warm on the ARM reference host) while specs/002-laya-reflexion-nodes/data-model.md line 76 says 3.0 — amend the plan document during review or revert the code default per plan: data-model config surface (contradicts)
