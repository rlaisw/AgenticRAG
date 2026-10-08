# Implementation Plan: Dual-System Workflow — Structured Decider + Reflexion Loop

**Branch**: `002-laya-reflexion-nodes` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-laya-reflexion-nodes/spec.md`

## Summary

Replace the current single-label routing (`fast|deliberative` classifier, keyword-heuristic de-facto primary) and monolithic deliberation loop with the two-system design: an **embedded System 1 decision node** — the Laya decision model (local ModernBERT + decision head, no text generation) returning route choice, 1–10 complexity score, and a calibrated yes/no sufficiency verdict in one pass — and a **System 2 reflexion graph** built on LangGraph with discrete Actor / Evaluator / Self-Reflector / Episodic Memory stages, evaluator-gated looping, and full-history memory conditioning. The keyword heuristic is demoted to outage-only fallback with provenance marking; the `ask` client contract is preserved field-for-field.

## Technical Context

**Language/Version**: Python 3.12 (project venv, package `agentic-rag-mcp`)

**Primary Dependencies**: mcp SDK 1.30 (`FastMCP`), `langgraph>=0.2` (already installed), httpx, LanceDB, CocoIndex, sentence-transformers — and, for the System 1 decision model: torch + transformers (already shipped for the embedder) + the `convaiinnovations/laya` checkpoint (~1.7 GB) with its `rl_agent_api` reference implementation. ONNX variant (`receptron/laya-onnx` + `onnxruntime`) is a later optimization, not v1.

**Storage**: Existing SQLite state + LanceDB vectors. Episodic memory is in-process and per-request — no persistence (FR-012).

**Testing**: pytest (51 tests currently: unit / integration / contract layout). New suites mirror that layout.

**Target Platform**: Linux (host venv today; Docker sidecar `agentic-rag` for Dify). Decision model adds ~2 GB RAM when loaded; container image impact is a tasks-phase packaging decision.

**Project Type**: library + MCP server (stdio + stateless streamable HTTP).

**Performance Goals**: routing decisions < 2 s for 95% of questions (SC-001; Laya runs ~140 ms warm on CPU); deliberation bounded by `max_iterations`; decision-node timeout default 3 s.

**Constraints**: FR-015 — the `ask` response contract must stay field-compatible (existing contract suite must pass unchanged); single-user local deployment; decision-model question/state limits (question options ≤ ~20, state truncated to 512 tokens).

**Scale/Scope**: single-user, small corpora; one decision-schema version.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is an unfilled template — no ratified gates exist. Applying the repo conventions established by spec-001 instead:

| Gate | Status | Evidence |
|---|---|---|
| Contract preservation | PASS | FR-015 pins the `ask` field set; contract suite stays green; new fields are additive (`decision`, `reflections`) |
| Tests-first | PASS | every new behavior (decision schema validation, evaluator verdicts, memory conditioning, fallback provenance) gets unit/integration checks; reflexion tests already exist from the interim implementation and are retained |
| Minimal dependencies | PASS | no new runtime service; decision model reuses torch/transformers already shipped; `langgraph` already a dependency; heuristic fallback code is demoted, not duplicated |

No violations. Re-checked after Phase 1 design below — still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-laya-reflexion-nodes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── decision-schema.md
│   └── ask-response.md
├── quickstart.md        # Phase 1 output
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/agentic_rag_mcp/
├── server.py              # ask wiring: decision node + reflexion graph; provenance marking
├── config.py              # + [decider] section (enabled, model repo/dir, timeout, noul threshold)
├── routing/
│   ├── decision.py        # NEW  System 1: embedded Laya decider — choice/score/noul in one pass + validation
│   ├── laya.py            # REMOVED (external app client superseded by decision.py)
│   ├── fallback.py        # DEMOTED: keyword heuristic, outage-only, provenance-marked
│   └── planner.py         # sub-task decomposition feeding the Actor stage
├── agents/
│   ├── reflexion.py       # NEW  System 2: LangGraph StateGraph — Actor/Evaluator/Self-Reflector/Memory
│   ├── evaluator.py       # NEW  rule-based score (1–10) + pass/fail verdict
│   ├── graph.py           # REMOVED (monolithic loop superseded by reflexion.py)
│   └── sufficiency.py     # DEMOTED: hit-count checks become an evaluator input, not the gate
└── …

tests/
├── unit/          # decision schema validation, evaluator verdicts, memory conditioning, fallback
├── contract/     # ask response field preservation (FR-015)
└── integration/  # end-to-end routes, reflexion convergence, decider-unavailable fallback
```

**Structure Decision**: single-project layout unchanged from spec-001; `routing/` gains `decision.py` and loses the external client; `agents/` gains the LangGraph graph + evaluator and loses the monolithic loop. Removals are explicit (FR-013) — old components are deleted, not left as dead code.

## Complexity Tracking

No constitution violations to justify. (Watch item, not a violation: the decision-model checkpoint is ~1.7 GB; loading it lazily and only when `[decider] enabled` keeps the default footprint unchanged.)
