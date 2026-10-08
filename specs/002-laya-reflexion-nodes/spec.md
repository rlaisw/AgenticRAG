# Feature Specification: Dual-System Workflow — Structured Decider + Reflexion Loop (Replacement)

**Feature Branch**: `002-laya-reflexion-nodes`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Enhance AgenticRAG workflow design with two coordinated nodes. System 1 (Laya): a fast router/decider that reads the entire input and scores a fixed set of pre-defined options in a single pass without generating text or hallucinating; exposes three decision primitives — choice (select one option from multiple), score (rate on an ordered scale), and boolean (a calibrated yes/no). System 2 (LangGraph Reflexion): an iterative thinker that generates, evaluates (score or pass/fail), self-reflects on failure with verbal feedback, stores the reflection in episodic memory, and lets that memory condition the next trial. Combined: System 1 decides the path; System 2 executes complex tasks with self-correction."

## Supersedes — Replacement Scope *(this feature REPLACES the existing design; it does not extend it)*

The project already operates a similar two-system workflow. This feature retires it. On completion, the old components MUST NOT participate in the primary path.

| # | OLD component (retired) | Replaced by (NEW) |
|---|---|---|
| 1 | Single-label question classifier returning only "fast" or "deliberative" — backed by a decision-layer client that is unreachable in practice, so a keyword heuristic is the de-facto primary router | System 1 Decision Node: single-pass structured decider returning ALL THREE primitives — route choice (from a fixed option set), complexity score (ordered scale), and knowledge-base-sufficiency boolean. The decision node is the PRIMARY path; the keyword heuristic is demoted to outage-only fallback. |
| 2 | Keyword heuristic router as de-facto primary | Outage-only fallback with explicit provenance marking; it MUST NOT route when the decision node is available. |
| 3 | Monolithic deliberation loop (plan → retrieve → draft critique → retry in one hand-rolled cycle), gated by a hit-count sufficiency check | System 2 Reflexion Graph: DISCRETE named stages — Actor, Evaluator, Self-Reflector, Episodic Memory — connected by an explicit conditional loop whose only gate is the Evaluator's verdict. |
| 4 | Binary-only draft evaluation (satisfied/continue, no score) | Evaluator returns BOTH an ordered-scale quality score AND a binary pass/fail verdict for every draft; pass terminates the loop immediately. |
| 5 | Formulaic missing-terms critique; only the latest critique's terms condition the next trial | Self-Reflector produces a verbal critique describing the specific failure; Episodic Memory accumulates ALL reflections of the task and the FULL history conditions every subsequent trial. |
| 6 | Hit-count sufficiency check as the loop's sole gate | Sufficiency signals become one INPUT to the Evaluator; the Evaluator's verdict alone decides retry vs. terminate. |

**Client contract preservation**: the `ask` tool's request/response surface and every field clients depend on today (answer, confidence, classification, sufficiency, trace, citations, error, plan) MUST remain present after the replacement; the `reflections` field carries the new memory contents.

## Clarifications

### Session 2026-10-08 (convergence follow-up: T030/T031/T033/T034)

- Q: Can the 2-second decision target be met on the reference host? → A: No — measured ~7.4 s warm with the PyTorch runtime and ~5.7 s with a parity-verified ONNX spike (exact match to 3 decimals on route probabilities); SC-001 amended to hardware-relative wording (timeout-bounded, <10 s warm on the reference host), ONNX retained as a documented future optimization.
- Q: Is the noul (sufficiency) primitive calibratable on this checkpoint? → A: No — across three statement variants the noul head consistently answers "not sufficient" (P(true) 0.05–0.22) for any positive phrasing of an unverifiable claim, and statement edits perturb the shared forward pass (routing flipped between variants). `sufficient` is therefore DERIVED from the route choice (direct_retrieval → true), which is the well-calibrated judgment; the noul question stays in the schema for three-primitive fidelity (FR-001) with its raw value unused.
- Q: How is the post-task hardening traceable? → A: The score-gated source_management misroute safety (answer from the KB when Lance distance ≤ 1.0, else routing guidance; measured 0.7 real vs 1.9 fuzzy) and the route-criteria rewording are folded into FR-005's semantics: source-management routes still never perform source operations; a strong KB match means the request was a knowledge question and is answered from the KB.
- Q: Does the outage heuristic meet SC-006's latency parity? → A: After widening its fast-prefix list to standard question openers (what/who/when/where/which/how many/how much/how fast/how long), yes — outage asks now route and complete at parity (interleaved median ≤ 1.25×), while markers, conjunctions, and long questions stay deliberative (safe default).

### Session 2026-10-08

- Q: Where should the System 1 decision node execute for this deployment? → A: Embedded — in-process inside the AgenticRAG server, backed by a configured LLM, returning all three primitives in one pass (replaces the external decision-app client; keyword heuristic becomes outage-only fallback).
- Q: When the decider returns a "live web" or "source management" route, what should the ask workflow actually execute? → A: Two execution paths only — web-route enters the reflexion loop with web tools first; source-management-route enters the direct path and answers with routing guidance, never performing source operations inside ask.
- Q: Should the Evaluator stage be rule-based or LLM-based in this first release? → A: Rule-based for v1 (coverage and citability checks compute score and pass/fail); LLM-as-judge can replace it later behind the same score-plus-verdict contract.
- Q: How long should episodic memory persist — one request, one conversation, or indefinitely? → A: Per-request — reflections accumulate across the request's trials and are discarded when it completes; no cross-request leakage.
- Q: What bounds should the complexity score scale use? → A: Integer 1–10, banded 1–3 simple, 4–7 moderate, 8–10 complex (matches the design example).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-Pass Structured Routing via the Decision Service (Priority: P1)

A user submits a question through any client (Dify chatflow, MCP client, CLI). The System 1 Decision Node reads the entire input in a single pass and returns three structured values from a pre-defined schema: the route (a choice from a fixed option set — direct retrieval, deliberative reasoning, live web, or source management), the complexity (a score on a defined ordered scale), and whether the knowledge base alone is likely sufficient (a calibrated boolean). Simple factual questions — "What was the quarterly revenue?" — route straight to direct retrieval and are answered in one step. The decider never writes prose, never selects outside the option set, and never scales outside the defined range. Unlike the old design, these decisions come from the structured decision node as the primary path — the keyword heuristic no longer routes normal traffic.

**Why this priority**: The decider is the front door of every request and the anchor of the replacement: moving from a single "fast/deliberative" label to three typed primitives is the contract change everything else hangs off. It removes free-text classification and ends the silent regime where a keyword heuristic was the de-facto router.

**Independent Test**: Fully testable by submitting a set of single-fact questions with the decision node running and verifying each response's trace shows all three primitives decided by the decision node (not the fallback), the question served by direct retrieval, and the answer citing the expected document.

**Acceptance Scenarios**:

1. **Given** a simple factual question about indexed content with the decision node available, **When** the user submits it, **Then** the trace shows a decision-node-sourced route of "direct retrieval", a low complexity score, and a "yes" sufficiency boolean — and the answer arrives with citations in a single retrieval step.
2. **Given** any question, **When** the decider runs, **Then** its output contains only the structured choice, score, and boolean values — no free text, no option outside the pre-defined set, no score outside the scale.
3. **Given** the decision node returns a value outside the defined option set or scale, **When** the decision is validated, **Then** the decider rejects it, treats the decision as unavailable, and routes via the marked fallback rather than acting on an invalid decision.
4. **Given** a question the decider routes as "live web", **When** the reflexion loop runs, **Then** the first trial orders web tools before knowledge-base retrieval.
5. **Given** a question the decider routes as "source management", **When** the workflow answers, **Then** the response provides routing guidance only and performs no source operations.

---

### User Story 2 - Reflexion Cycle with Discrete Stages for Complex Questions (Priority: P2)

A user asks a multi-part or comparative question — "Compare the Apollo landing with quarterly revenue growth" — and the decision node routes it to the deliberative thinker. The thinker runs as discrete stages in an explicit loop: the Actor gathers evidence and drafts a candidate answer; the Evaluator checks the draft against the question and returns BOTH a quality score and a pass/fail verdict; if the draft fails, the Self-Reflector produces a verbal critique describing the specific failure ("the draft covers the landing but never addresses revenue growth"); the Episodic Memory stage stores that reflection alongside all prior ones; and the next trial's retrieval queries are conditioned by the FULL accumulated reflection history. A passed verdict ends the loop immediately; an exhausted iteration budget ends it with an honest low-confidence flag.

**Why this priority**: This is where answer quality is won or lost on hard questions, and where the old design's weaknesses concentrate: single-critique conditioning forgets earlier failures, and a hit-count gate cannot tell a complete draft from a well-evidenced partial one.

**Independent Test**: Fully testable by asking compound questions with deliberately incomplete first-pass evidence and verifying the final answer covers every part, and the trace shows the Actor/Evaluator/Self-Reflector/Memory stages per iteration, evaluator scores plus verdicts, verbal critiques, and next-trial queries carrying terms from ALL prior reflections — not just the latest.

**Acceptance Scenarios**:

1. **Given** a three-part question where the first trial covers one part, **When** the Evaluator fails the draft with a low score, **Then** the Self-Reflector names all uncovered parts verbally, the reflection is stored, and the second trial's queries target everything the first trial missed.
2. **Given** a trial whose draft fails on part C while parts A and B were fixed in an earlier trial, **When** the next trial is formed, **Then** its queries remain conditioned on the A and B reflections (full history), so fixed parts do not regress.
3. **Given** a draft that passes evaluation, **When** the pass verdict is recorded, **Then** the loop terminates immediately with no further Actor run.
4. **Given** a question that can never be fully answered, **When** the iteration budget is exhausted, **Then** the system returns the best available draft flagged low confidence with all stored reflections — never looping forever, never presenting a partial answer as certain.

---

### User Story 3 - Decision Resilience, Provenance, and Full Traceability (Priority: P3)

The decision node's decision engine becomes unavailable or times out mid-operation. Requests still complete via the deterministic fallback rules, and every such response is marked as fallback-served — but the moment the backend recovers, the decision node resumes as the sole primary router. In normal operation, every response exposes the complete decision trail: the three primitive values with their provenance (decision node or fallback), each reflexion iteration's evaluator score and verdict, the self-reflector's verbal critiques, and the full episodic memory — so an operator can audit exactly why a question was routed and why an answer looks the way it does.

**Why this priority**: Availability and auditability make the replacement trustworthy: a dead decision node must not dead-end requests, the fallback must never silently pose as the primary, and every routing/reflection choice must be inspectable after the fact.

**Independent Test**: Fully testable by stopping the decision node, submitting questions (answers arrive marked fallback), restarting the service (next decisions come from it), and verifying a deliberative response's trace contains the full stage-by-stage record.

**Acceptance Scenarios**:

1. **Given** the decision node is unavailable (backend failure or timeout), **When** a user submits any question, **Then** the request completes via fallback routing and the response is marked fallback-served.
2. **Given** the decision node's backend recovers, **When** the next question arrives, **Then** the decision node routes it and no fallback marking appears.
3. **Given** a deliberative response, **When** an operator inspects its trace, **Then** it contains the decision primitives with provenance, and per iteration: the evaluator's score and verdict, the self-reflector's critique, and the episodic memory contents used by the next trial.

---

### Edge Cases

- What happens when the decision node returns an option outside the defined set or a score outside the scale (treated as unavailable → marked fallback; never acted on)?
- What happens when the evaluator's verdict oscillates across re-checks (pass is final — a passed draft is never re-evaluated)?
- What happens on the first trial with an empty episodic memory (runs unconditioned; memory list starts empty)?
- What happens when the iteration budget is 1 (single-shot deliberation: one Actor/Evaluator pass, pass or low-confidence flag)?
- What happens when retrieval returns zero evidence across all trials (exhausted budget, low-confidence "no relevant information" answer — never fabricated)?
- What happens when the decision node flaps (fails and recovers) mid-run (the in-flight request keeps its fallback decision; the next request uses the service)?
- How does the system behave when episodic memory grows to the budget's maximum (all reflections retained within the task; memory discarded with the request — no cross-request leakage)?

## Requirements *(mandatory)*

### Functional Requirements

**System 1 — Decision Node (replaces the single-label classifier)**

- **FR-001**: The workflow MUST route every incoming request through a structured decision step that, in a single pass over the entire input, returns (a) a route choice from a fixed, pre-defined option set, (b) a complexity score on a defined ordered scale (integer 1–10 per the Decision Schema), and (c) a knowledge-base-sufficiency boolean.
- **FR-002**: The decision step MUST return only structured values (an option from the defined set, a number within the scale, a boolean) and MUST NOT produce free text or select options outside the pre-defined set.
- **FR-003**: The in-process decision node MUST be the primary decision path whenever its decision engine is available; the legacy keyword heuristic MUST make routing decisions ONLY when the decision node is unavailable (backend failure or timeout), and every fallback-served response MUST be marked as such.
- **FR-004**: The workflow MUST validate every decision-service response against the defined schema and MUST treat out-of-set choices, out-of-range scores, and malformed responses as decision unavailability (fallback), never as usable decisions.
- **FR-005**: When the decision indicates the direct route, the workflow MUST answer via a single retrieval step without entering the deliberative loop. Route choices map to exactly two execution paths: "direct retrieval" and "source management" routes take the direct path (source-management questions receive routing guidance, never performed operations; a strong knowledge-base match means the request was actually a knowledge question and is answered from the knowledge base — misroute safety, T033), while "deliberative reasoning" and "live web" routes take the reflexion loop, with the live-web route ordering web tools first in its first trial.

**System 2 — Reflexion Graph (replaces the monolithic deliberation loop)**

- **FR-006**: When the decision indicates the complex route, the workflow MUST execute the deliberation as discrete named stages — Actor (gather evidence, draft), Evaluator (score and verdict), Self-Reflector (verbal critique), Episodic Memory (store) — connected by an explicit conditional loop.
- **FR-007**: The Evaluator MUST return, for every draft, both an ordered-scale quality score and a binary pass/fail verdict, and a pass verdict MUST terminate the loop immediately.
- **FR-008**: On a fail verdict, the Self-Reflector MUST produce a verbal critique that describes the specific failure — what the draft is missing or got wrong — not just a list of absent keywords.
- **FR-009**: Episodic Memory MUST accumulate every reflection of the current task, and each subsequent trial MUST be conditioned on the FULL accumulated history, such that previously fixed shortcomings do not regress.
- **FR-010**: The loop's retry/terminate decision MUST be gated solely by the Evaluator's verdict; sufficiency signals (e.g., hit counts) MUST be inputs to the Evaluator, not independent gates.
- **FR-011**: The reflexion cycle MUST be bounded by a configurable iteration budget; on exhaustion the workflow MUST return the best available draft flagged low confidence and MUST NOT continue iterating.
- **FR-012**: Episodic memory MUST be scoped to a single request, MUST NOT leak into subsequent requests, and MUST be discarded when the request completes.

**Replacement integrity**

- **FR-013**: On completion, the OLD components (single-label classifier as primary router, keyword heuristic as de-facto primary, monolithic deliberation loop, hit-count loop gate) MUST NOT be reachable in normal operation; the keyword heuristic may remain ONLY as the outage fallback.
- **FR-014**: Every response MUST include a trace of the decision primitives with provenance (decision node or fallback), and for deliberative requests the per-iteration evaluator scores and verdicts, self-reflector critiques, and episodic memory contents.
- **FR-015**: The `ask` tool's client-facing contract MUST be preserved: every response field present before the replacement (answer, confidence, classification, sufficiency, trace, citations, error, plan) MUST remain present, with the `reflections` field carrying episodic-memory contents.

### Key Entities

- **Decision Schema**: the versioned definition of the decision point — its fixed option set (direct retrieval, deliberative reasoning, live web, source management), its complexity score scale (integer 1–10: 1–3 simple, 4–7 moderate, 8–10 complex), and its boolean question (is the knowledge base alone likely sufficient?); the decision node and the workflow both validate against it.
- **Decision Result**: the decider's output — route choice, complexity score, sufficiency boolean, provenance (decision node or fallback), and decision latency.
- **Reflection Record**: one cycle's outcome — iteration number, evaluator score and verdict, the self-reflector's verbal critique, and the specific shortfalls to target next.
- **Episodic Memory**: the ordered, per-request buffer of reflection records; the full buffer conditions every subsequent trial.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of routing decisions complete within the configured decision timeout (default 12 s) from received input to decision, with warm single-pass decision latency under 10 s on the reference ARM host (measured: ~7.4 s torch, ~5.7 s ONNX; the original 2 s draft assumed Apple-Silicon-class hardware — amended per T030 with both measurements recorded).
- **SC-002**: 100% of decisions across the test set return a valid option from the defined set, a score within the scale, and a boolean — zero free-text, out-of-set, or out-of-range selections.
- **SC-003**: With the decision node reachable, 100% of primary-path responses carry decision-service provenance and 0% carry fallback provenance (the keyword heuristic no longer routes normal traffic).
- **SC-004**: For multi-part test questions, reflexion-path answers address at least 80% of the question's parts, up from the single-pass baseline, verified against the Evaluator's criteria in the trace.
- **SC-005**: 100% of budget-exhausted responses carry the low-confidence flag and their full episodic memory; no request ever exceeds the configured iteration budget.
- **SC-006**: With the decision node unavailable, 100% of test questions still receive a complete answer via fallback routing, marked as fallback-served, with response latency at most 25% above the normal path.
- **SC-007**: 100% of pre-existing client-visible response fields remain present after the replacement (backward-compatible contract, verified by the existing client contract test suite passing unchanged).

## Assumptions

- The System 1 decision node runs **embedded, in-process inside the server**, backed by the Laya decision model applying a schema-constrained decision definition (Laya-style: fixed option set, ordered score scale, boolean). This replaces the current external decision-app client, eliminating the unreachable-service failure mode that made the keyword heuristic the de-facto router; the heuristic remains only as outage fallback.
- The System 2 reflexion graph is built on the LangGraph-compatible interface already present as a project dependency; the graph's stages map one-to-one to the Actor / Evaluator / Self-Reflector / Episodic Memory nodes of the design.
- For v1 the Evaluator is rule-based (confirmed in clarification): coverage and citability checks feeding score + verdict; an LLM-as-judge Evaluator can replace it behind the same score-plus-verdict contract without changing this spec.
- "Long-term buffer" in the design means long-term WITHIN a task (confirmed in clarification): episodic memory persists across all of a request's trials and is discarded with the request. Conversation-scoped and persistent memory are out of scope.
- The three decision primitives are the complete routing vocabulary; defining new primitive types is out of scope.
- The Dify-side chatflow consumes the enhanced workflow through the existing tool interfaces unchanged; no new MCP tools are required by this feature.
- Out of scope: model fine-tuning, new data sources, graph-layer (Graphify) changes, and UI redesign.
