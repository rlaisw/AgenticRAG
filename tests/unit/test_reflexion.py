"""ReflexionAgent end-state behavior on the new LangGraph graph.

The full stage-by-stage behavior (verdict gating, union conditioning, budget,
web-first) is covered by tests/unit/test_reflexion_graph.py; this file pins the
TOD-contract: honest no-evidence answers and never presenting partial as certain
(spec FR-011, SC-005).
"""

from agentic_rag_mcp.agents.reflexion import ReflexionAgent


def test_no_evidence_answer_is_honest_never_fabricated():
    out = ReflexionAgent({"vector_search": lambda q: []}, max_iterations=2).run(
        "What is the CEO's name?")
    assert "could not find sufficient information" in out["answer"]
    assert out["confidence"] == "low"
    assert out["citations"] == []
    assert out["error"] is not None


def test_budget_exhaustion_flags_low_confidence():
    def empty(query):
        return []

    out = ReflexionAgent({"vector_search": empty}, max_iterations=2).run(
        "What happened on Mars last Tuesday?")
    assert out["sufficiency"] == "exhausted"
    assert out["confidence"] == "low"
    assert out["error"] is not None
    assert len(out["reflections"]) >= 1
