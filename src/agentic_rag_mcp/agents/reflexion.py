"""System 2: LangGraph reflexion graph (FR-006..FR-011; research.md D3/D6).

Discrete stages — Actor / Evaluator / Self-Reflector / Episodic Memory — with an
explicit conditional loop whose only gate is the Evaluator's verdict. Episodic
memory accumulates every reflection of the task; each subsequent trial is
conditioned on the union of all missing-focus terms (no regression of fixed
parts). Replaces the retired monolithic loop (agents/graph.py, FR-013).
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..errors import SufficiencyExhausted
from ..routing.planner import decompose
from . import synthesis
from .evaluator import evaluate
from .memory import EpisodicMemory, ReflectionRecord

_WEB_TOOLS = ("web_search", "fetch_url")


class _State(TypedDict, total=False):
    question: str
    tools: dict
    budget: int
    web_first: bool
    tasks: list
    evidence: list
    trace: list
    fetched_urls: list
    iterations: int
    draft: str
    score: int
    verdict: str
    missing: list
    critique: str
    memory: Any            # EpisodicMemory
    exhausted: bool
    confidence: str


# ---- Actor: retrieve + draft, conditioned on the memory union terms (FR-009) ----

def _actor(state: _State) -> dict:
    tools, question = state["tools"], state["question"]
    memory: EpisodicMemory = state["memory"]
    if state["iterations"] == 0:
        tasks = decompose(question, [t for t in tools])
        if state.get("web_first"):  # live_web route: web tools lead trial 1 (FR-005)
            if not any(t["tool"] in _WEB_TOOLS for t in tasks):
                tasks.insert(0, {"id": "t0", "tool": "web_search", "input": question})
            tasks.sort(key=lambda t: 0 if t["tool"] in _WEB_TOOLS else 1)
    else:
        extra = " ".join(memory.union_missing_focus())
        tasks = state["tasks"]
        tasks = [{"id": t["id"], "tool": t["tool"],
                  "input": f"{t['input']} {extra}".strip()} for t in tasks]

    trace, evidence = state["trace"], state["evidence"]
    fetched = set(state["fetched_urls"])
    for task in tasks:
        tool = tools.get(task["tool"])
        if not tool:
            continue
        try:
            hits = tool(task["input"]) or []
        except Exception as exc:  # noqa: BLE001 — tool isolation
            hits = []
            task["error"] = str(exc)
        trace.append({"tool": task["tool"], "query": task["input"], "hits": len(hits)})
        task["results"] = hits
        evidence.extend(hits)
        # FR-012: the web_search tool itself now yields grouped page content as
        # evidence (server-side research pipeline); the prior single-page
        # fetch enrichment here is superseded and removed.
    return {
        "tasks": tasks, "trace": trace, "evidence": evidence,
        "fetched_urls": list(fetched),
        "iterations": state["iterations"] + 1,
        "draft": synthesis.synthesize(question, evidence, "normal"),
    }


def _evaluator(state: _State) -> dict:
    score, verdict, missing = evaluate(state["question"], state["draft"], state["evidence"])
    memory: EpisodicMemory = state["memory"]
    if verdict == "pass":
        # pass is final (FR-007) but the verdict is still recorded (FR-014, SC-005)
        memory.append(ReflectionRecord(
            iteration=state["iterations"], evaluator_score=score,
            evaluator_verdict="pass",
            critique="draft addresses the question with citable sources",
            missing_focus=[],
        ))
    return {"score": score, "verdict": verdict, "missing": missing, "memory": memory}


# ---- Self-Reflector: verbal critique of the specific failure (FR-008) ----

def _self_reflector(state: _State) -> dict:
    parts = []
    if state["evidence"]:
        parts.append("The draft draws on gathered evidence")
    else:
        parts.append("No evidence was gathered at all")
    if state["missing"]:
        parts.append(f"but does not address: {', '.join(state['missing'])}")
    else:
        parts.append("but lacks citable sources")
    critique = (". ".join(parts) +
                f". The next trial must target: {', '.join(state['missing']) or 'citable sources'}.")
    return {"critique": critique}


# ---- Episodic Memory: store the reflection (FR-009); the union conditions trials ----

def _memory_node(state: _State) -> dict:
    memory: EpisodicMemory = state["memory"]
    memory.append(ReflectionRecord(
        iteration=state["iterations"],
        evaluator_score=state["score"],
        evaluator_verdict=state["verdict"],
        critique=state["critique"],
        missing_focus=list(state["missing"]),
    ))
    return {"memory": memory}


def _after_evaluator(state: _State) -> str:
    """The Evaluator's verdict alone gates the loop (FR-007, FR-010)."""
    if state["verdict"] == "pass":
        return END
    return "self_reflector"


def _after_memory(state: _State) -> str:
    if state["iterations"] >= state["budget"]:
        return END
    return "actor"


def _build_graph() -> Any:
    g = StateGraph(_State)
    g.add_node("actor", _actor)
    g.add_node("evaluator", _evaluator)
    g.add_node("self_reflector", _self_reflector)
    g.add_node("memory", _memory_node)
    g.add_edge(START, "actor")
    g.add_edge("actor", "evaluator")
    g.add_conditional_edges("evaluator", _after_evaluator)
    g.add_edge("self_reflector", "memory")
    g.add_conditional_edges("memory", _after_memory)
    return g.compile()


class ReflexionAgent:
    """Same interface as the retired loop: ReflexionAgent(tools).run(question)."""

    def __init__(self, tools: dict, max_iterations: int = 5) -> None:
        self._tools = tools
        self._budget = max_iterations
        self._graph = _build_graph()

    def run(self, question: str, web_first: bool = False) -> dict:
        final: _State = self._graph.invoke({
            "question": question, "tools": self._tools, "budget": self._budget,
            "web_first": web_first, "tasks": [], "evidence": [], "trace": [],
            "fetched_urls": [], "iterations": 0, "memory": EpisodicMemory(),
            "exhausted": False,
        })
        passed = final["verdict"] == "pass"
        exhausted = not passed and final["iterations"] >= self._budget
        confidence = "normal" if passed else "low"
        answer = synthesis.synthesize(question, final["evidence"], confidence)
        memory: EpisodicMemory = final["memory"]
        return {
            "answer": answer,
            "confidence": confidence,
            "classification": "deliberative",
            "iterations": final["iterations"],
            "sufficiency": "satisfied" if passed else "exhausted",
            "trace": final["trace"],
            "reflections": memory.to_list(),
            "citations": synthesis.citations(final["evidence"]),
            "error": SufficiencyExhausted("iteration budget exhausted").to_result()
                     if exhausted else None,
            "plan": [{"id": t["id"], "tool": t["tool"], "input": t["input"]}
                     for t in final["tasks"]],
        }
