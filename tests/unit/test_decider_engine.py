"""Decider engine mapping and failure modes with the model mocked (FR-002, FR-004).

Mapping (research.md D4): choice argmax, score rounded+clamped to integer 1-10,
noul thresholded. Failures (timeout, malformed, load error) => invalid result.
"""

import agentic_rag_mcp.routing.laya_runtime as rt
from agentic_rag_mcp.routing import decision


def test_mapping_from_model_output():
    out = {"answers": {
        "route": {"type": "choice", "choice": "deliberative_reasoning",
                  "probabilities": {"direct_retrieval": 0.2, "deliberative_reasoning": 0.7,
                                     "live_web": 0.08, "source_management": 0.02}},
        "complexity": {"type": "score", "score": 6.42},
        "sufficient": {"type": "noul", "noul": 0.31},
    }}
    r = decision.map_model_output(out, threshold=0.5)
    assert r.route == "deliberative_reasoning"
    assert r.complexity == 6
    assert r.sufficient is False
    assert r.route_probabilities["deliberative_reasoning"] == 0.7
    assert r.valid is True


def test_score_clamped_to_1_10():
    r = decision.map_model_output({"answers": {
        "route": {"choice": "live_web", "probabilities": {}},
        "complexity": {"score": 11.7},
        "sufficient": {"noul": 0.9}}}, threshold=0.5)
    assert r.complexity == 10


def test_questions_shape_is_three_primitives():
    q = decision._questions()
    assert set(q) == {"route", "complexity", "sufficient"}
    assert q["route"]["type"] == "choice" and len(q["route"]["criteria"]) == 4
    assert q["complexity"]["type"] == "score" and len(q["complexity"]["criteria"]) == 10
    assert q["sufficient"]["type"] == "noul"


def test_timeout_yields_invalid(monkeypatch):
    def boom(cfg, state, questions):
        raise TimeoutError()

    monkeypatch.setattr(rt, "system_one", boom)
    r = decision.decide("any question", decision._test_cfg())
    assert r.valid is False and r.route is None


def test_malformed_output_yields_invalid(monkeypatch):
    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: {"answers": {}})
    r = decision.decide("any question", decision._test_cfg())
    assert r.valid is False


def test_decide_records_latency(monkeypatch):
    monkeypatch.setattr(rt, "system_one",
                        lambda cfg, s, q: {"answers": {
                            "route": {"choice": "direct_retrieval", "probabilities": {}},
                            "complexity": {"score": 2.2},
                            "sufficient": {"noul": 0.8}}})
    r = decision.decide("q", decision._test_cfg())
    assert r.valid and r.latency_ms >= 0


def test_fallback_route_maps_labels_and_marks_provenance():
    r = decision.fallback_route("What is the moon landing date?")   # heuristic: fast
    assert r.provenance == "fallback"
    assert r.route in ("direct_retrieval", "deliberative_reasoning")
    assert isinstance(r.complexity, int) and 1 <= r.complexity <= 10
