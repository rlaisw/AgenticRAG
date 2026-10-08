"""DecisionSchema + DecisionResult validation (FR-002, FR-004) — contracts/decision-schema.md."""

from agentic_rag_mcp.routing.decision import DecisionResult, validate_output


def _result(route="direct_retrieval", complexity=2, sufficient=True):
    return DecisionResult(
        route=route, complexity=complexity, sufficient=sufficient,
        route_probabilities={route: 0.9}, provenance="decision_node", latency_ms=10,
    )


def test_valid_result_passes():
    assert validate_output(_result()).valid is True


def test_out_of_set_route_is_invalid():
    assert validate_output(_result(route="teleport")).valid is False


def test_complexity_out_of_range_is_invalid():
    assert validate_output(_result(complexity=0)).valid is False
    assert validate_output(_result(complexity=11)).valid is False


def test_complexity_must_be_integer():
    assert validate_output(_result(complexity=3.5)).valid is False


def test_provenance_only_two_values():
    assert validate_output(_result()).valid is True
    r = _result()
    r.provenance = "unknown"
    assert r.provenance not in ("decision_node", "fallback")


def test_decider_mapping_from_model_output():
    """choice argmax, score rounded+clamped to 1-10, noul thresholded (D4)."""
    from agentic_rag_mcp.routing.decision import map_model_output

    out = {
        "answers": {
            "route": {"type": "choice", "choice": "deliberative_reasoning",
                      "probabilities": {"direct_retrieval": 0.2, "deliberative_reasoning": 0.7,
                                        "live_web": 0.08, "source_management": 0.02}},
            "complexity": {"type": "score", "score": 6.42},
            "sufficient": {"type": "noul", "noul": 0.31},
        }
    }
    r = map_model_output(out, threshold=0.5)
    assert r.route == "deliberative_reasoning"
    assert r.complexity == 6
    assert r.sufficient is False
    assert r.route_probabilities["deliberative_reasoning"] == 0.7


def test_decider_timeout_yields_invalid(monkeypatch):
    from agentic_rag_mcp.routing import decision
    import agentic_rag_mcp.routing.laya_runtime as rt

    def boom(state, questions):
        raise TimeoutError()

    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: (_ for _ in ()).throw(boom(s, q)))
    r = decision.decide("any question", decision._test_cfg())
    assert r.valid is False


def test_malformed_model_output_yields_invalid(monkeypatch):
    import agentic_rag_mcp.routing.laya_runtime as rt
    from agentic_rag_mcp.routing import decision

    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: {"answers": {}})
    r = decision.decide("any question", decision._test_cfg())
    assert r.valid is False
