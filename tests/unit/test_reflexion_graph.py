"""Reflexion graph (FR-006..FR-011): discrete stages, evaluator-gated loop, memory conditioning."""

from agentic_rag_mcp.agents.reflexion import ReflexionAgent


def test_graph_runs_until_pass_and_stops():
    """Pass verdict ends the loop immediately — no further Actor run (US2 AC3)."""
    calls = []

    def fake_vector(query):
        calls.append(query)
        return [{"snippet": "the voyager launch happened in 1977", "document_id": "d2"}]

    out = ReflexionAgent({"vector_search": fake_vector}, max_iterations=4).run(
        "When did the voyager launch?")
    assert out["sufficiency"] == "satisfied"
    assert out["confidence"] == "normal"
    assert out["iterations"] == 1          # passed on the first trial
    assert len(out["reflections"]) == 1
    assert out["reflections"][0]["evaluator_verdict"] == "pass"
    assert out["error"] is None


def test_fail_triggers_reflector_memory_and_conditioned_retry():
    """US2 AC1: fail -> verbal critique -> memory -> retry with the missing terms."""
    calls = []

    def fake_vector(query):
        calls.append(query)
        if len(calls) == 1:
            return [{"snippet": "unrelated mission notes", "document_id": "d1"}]
        return [{"snippet": "the voyager launch happened in 1977", "document_id": "d2"}]

    out = ReflexionAgent({"vector_search": fake_vector}, max_iterations=3).run(
        "When did the voyager launch?")
    assert len(calls) >= 2
    assert "voyager" in calls[1]                      # missing terms enter the retry query
    recs = out["reflections"]
    assert recs[0]["evaluator_verdict"] == "fail"
    assert recs[0]["evaluator_score"] >= 1
    assert "voyager" in recs[0]["critique"]          # verbal critique names the failure (FR-008)
    assert out["sufficiency"] == "satisfied"


def test_full_history_conditions_each_trial_no_regression():
    """US2 AC2: terms fixed in an earlier trial persist in later trials (union, not latest)."""
    calls = []

    def fake_vector(query):
        calls.append(query)
        # trial 1 misses everything; trial 2 fixes apollo/landing but still misses
        # neptune/probe; trial 3 must keep apollo terms (union of ALL records)
        if len(calls) == 1:
            return [{"snippet": "space missions are historic", "document_id": "d1"}]
        if len(calls) == 2:
            return [{"snippet": "the apollo landing on the moon 1969",
                     "document_id": "d1"}]
        return [{"snippet": "details describe apollo landing moon 1969 and the neptune probe launch 1977",
                 "document_id": "d2"}]

    out = ReflexionAgent({"vector_search": fake_vector}, max_iterations=3).run(
        "Describe apollo landing neptune probe details")
    assert len(calls) == 3, "two failing trials should force a third"
    third = calls[2]
    assert "apollo" in third      # fixed in trial 2 — must NOT regress in trial 3 (FR-009)
    assert "neptune" in third     # still missing in trial 2 — union carries it forward
    assert out["sufficiency"] == "satisfied"


def test_budget_exhaustion_low_confidence_and_full_memory():
    out = ReflexionAgent({"vector_search": lambda q: []}, max_iterations=2).run(
        "What happened on Mars last Tuesday?")
    assert out["sufficiency"] == "exhausted"
    assert out["confidence"] == "low"
    assert out["error"] is not None
    assert out["iterations"] == 2
    assert len(out["reflections"]) == 2                 # full memory on exhaustion (SC-005)
    assert all(r["evaluator_verdict"] == "fail" for r in out["reflections"])


def test_web_first_orders_web_tools_in_first_trial():
    """FR-005: live_web route leads trial 1 with web tools."""
    order = []

    def fake_web(query):
        order.append("web")
        return []

    def fake_vector(query):
        order.append("vector")
        return [{"snippet": "some answer text answer", "document_id": "d"}]

    ReflexionAgent({"web_search": fake_web, "vector_search": fake_vector},
                   max_iterations=1).run("current time in hong kong", web_first=True)
    assert order[0] == "web"


def test_contract_fields_present():
    out = ReflexionAgent({"vector_search": lambda q: [
        {"snippet": "voyager launch 1977", "document_id": "d"}]}, max_iterations=2).run(
        "voyager launch year")
    for field in ("answer", "confidence", "classification", "iterations", "sufficiency",
                  "trace", "reflections", "citations", "error", "plan"):
        assert field in out, f"missing contract field: {field}"
    assert out["classification"] == "deliberative"
