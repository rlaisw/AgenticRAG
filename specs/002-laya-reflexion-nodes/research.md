# Research: Dual-System Workflow — Structured Decider + Reflexion Loop

**Feature**: specs/002-laya-reflexion-nodes/spec.md | **Date**: 2026-10-08

Phase 0 research findings. All [NEEDS CLARIFICATION]-class unknowns resolved.

## D1 — System 1 engine: local Laya decision model, not an LLM prompt

**Decision**: The embedded decision node runs the actual Laya decision model (Convai Innovations' System 1 model — ModernBERT encoder + decision head) in-process, invoked through its `system_one` API with our three-primitive schema.

**Rationale**: The referenced repo (`receptron/laya`) documents Laya as a decision model that "does not generate text" — one forward pass returns every answer with calibrated probabilities: `choice` (option + probability per option), `score` (expected level on an ordered rubric + distribution), `noul` (calibrated P(true) for a yes/no statement — this is the spec's boolean primitive). This makes FR-002 structural rather than prompt-engineered: no free text can exist because the model cannot produce it. Warm inference is ~140 ms on CPU, comfortably inside SC-001's 2 s. The spec's FR-003 wording "LLM backend" (from clarify Q1-A) is amended to "decision engine" to match the real engine — see plan completion report.

**Alternatives considered**:
- Schema-constrained LLM prompting (OpenAI-compatible backend): rejected — reintroduces text generation (violating the "without generating text or hallucinating" design requirement), adds per-request cost/latency/variance, and needs prompt-tuning to stay in-schema.
- External Laya app (HTTP): rejected in clarification Q1 (embedded, in-process).

## D2 — Decision model runtime: PyTorch reference first, ONNX later

**Decision**: Run the Python reference implementation (`rl_agent_api`) with the `convaiinnovations/laya` Hugging Face checkpoint. torch + transformers + safetensors are already installed (used by the embedder); only the checkpoint download (~1.7 GB, cached) and the reference API files are new. ONNX (`receptron/laya-onnx` + `onnxruntime`, ~2 GB RAM loaded) is a later optimization if memory or startup time matters; the `system_one` request/response shape is identical to the reference, so the swap is internal.

**Rationale**: zero new runtime dependencies on the torch path; identical outputs to four decimal places per the repo README; model limits (≤ ~20 options per choice question, 192-token question budget, 512-token state truncation) are compatible with our schema (4 routes, one-line questions).

**Alternatives considered**: ONNX-first (rejected for v1 — extra export step + onnxruntime dep for identical behavior); Node.js package via subprocess (rejected — wrong runtime, process-boundary complexity).

## D3 — System 2 execution: LangGraph StateGraph with evaluator-gated conditional edges

**Decision**: Build the reflexion loop as a LangGraph `StateGraph` with four nodes — Actor, Evaluator, Self-Reflector, Episodic Memory — and a conditional edge that returns to Actor only on a fail verdict, END on pass or exhausted budget. `langgraph>=0.2` is already a project dependency (installed in the venv), and the user's referenced pattern (langgraph-reflection `llm_as_a_judge.py`: Actor → Judge → loop-if-fail) is exactly this shape.

**Rationale**: matches the design diagram one-to-one; conditional edges make the "evaluator verdict is the sole gate" (FR-010) literal; the retired monolithic while-loop (agents/graph.py) had no discrete stages and mixed gating concerns.

**Alternatives considered**: retain the hand-rolled loop with stage methods (rejected — FR-006 requires discrete named stages; the loop's old shape is exactly what the spec retires).

## D4 — Score and boolean mapping

**Decision**: The 1–10 complexity score is a 10-level ordered rubric passed to Laya's `score` primitive; the returned expected level is rounded to the nearest integer and banded (1–3 simple, 4–7 moderate, 8–10 complex). The sufficiency boolean uses Laya's `noul` (calibrated P(true)) with a configurable threshold, default 0.5. Route selection uses `choice` over exactly four options; `argmax` of the probability distribution is the decision; validation rejects anything else (FR-004).

**Rationale**: preserves the primitives' calibrated-probability semantics while pinning the concrete schema required by the spec's Decision Schema entity; thresholds are config-driven so tuning doesn't change the contract.

**Alternatives considered**: binary route choice only (rejected — spec pins three primitives); LLM-judged scoring (rejected in clarification Q3 for the evaluator, same logic applies to routing).

## D5 — Rule-based Evaluator (confirmed) and its scoring formula

**Decision**: The Evaluator computes: coverage (fraction of question content-terms present in the draft), citability (≥ 1 citable evidence item), and an input signal from the legacy sufficiency check (hit counts). Score = 1–10 mapped from coverage and citability (e.g., 10 × coverage, halved when no citations); pass = coverage ≥ threshold AND citable evidence present. Deterministic, unit-testable, no cost.

**Rationale**: clarification Q3 confirmed rule-based v1 behind the score+verdict contract; determinism keeps reflexion-loop tests reproducible; the contract allows an LLM-as-judge swap later without spec change.

**Alternatives considered**: LLM-as-judge day one (rejected in Q3); hybrid judge-for-score-only (rejected — verdict would still be nondeterministic, defeating the gate).

## D6 — Full-history memory conditioning

**Decision**: Episodic memory is an ordered per-request list; each trial's query formulation is conditioned on the UNION of missing-focus terms across all stored reflections (previously-fixed terms persist in the query, matching FR-009's no-regression requirement), and the full record list is emitted in the response (`reflections` field).

**Rationale**: the retired design appended only the latest critique's terms, allowing regressions; union-conditioning is a one-line change to the reformulation step and directly testable (three-part question test).

**Alternatives considered**: only-latest conditioning (rejected — the regression scenario in US2 AC2); persistent/conversation store (rejected in clarification Q4).

## D7 — Fallback and provenance semantics

**Decision**: Any decider failure (model not loaded, timeout > 3 s default, malformed/invalid output) routes through the keyword heuristic with `provenance: "fallback"` in the response trace; recovery is automatic on the next request (no state). Existing `DecisionLayerUnavailable` semantics are reused. FR-013 removal is literal: `routing/laya.py` (external client) and `agents/graph.py` (monolithic loop) are deleted; `fallback.py` and `sufficiency.py` stay in demoted roles.

**Rationale**: preserves current availability behavior while making provenance first-class (FR-014); deletion (not deprecation) satisfies the spec's "not reachable in normal operation".

**Alternatives considered**: keep old classes behind a flag (rejected — FR-013 forbids dead code paths); hard-fail on decider loss (rejected — FR-007/SC-006 require graceful fallback).

## D8 — Client contract preservation

**Decision**: `ask` keeps every existing response field; `decision` (route, complexity, sufficient, provenance, latency_ms) and `reflections` (already additive) are new fields. The existing contract test suite must pass unchanged (FR-015 / SC-007); `classification` keeps its values (`fast|deliberative|deliberative-fallback` style provenance flows through `decision.provenance`).

**Rationale**: zero breakage for the Dify chatflow and existing tests; provenance is additive.

**Alternatives considered**: reshape the response around the new primitives (rejected — SC-007 forbids contract breakage).
