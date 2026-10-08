"""US3: fallback provenance + recovery (FR-003, FR-007, SC-006)."""

import asyncio
import json

import pytest

from agentic_rag_mcp.config import Config
from agentic_rag_mcp.server import build_server


def call(server, name, args=None):
    raw = asyncio.run(server.call_tool(name, {} if args is None else args))
    structured = [b["result"] for b in raw if isinstance(b, dict) and "result" in b]
    if structured:
        return structured[0]
    texts = [getattr(b, "text", "") for b in raw if getattr(b, "text", "")]
    joined = "".join(texts).strip()
    return json.loads(joined) if joined else None


@pytest.fixture()
def server(tmp_path, corpus, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = Config(state_db=tmp_path / "state.sqlite3", vector_dir=tmp_path / "vector",
                 decider_enabled=False, max_iterations=2)  # outage: decider disabled
    return build_server(cfg), corpus


def test_outage_routes_via_fallback_and_marks_it(server):
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    ans = call(srv, "ask", {"question": "What is the speed of light?"})
    assert ans["decision"]["provenance"] == "fallback"
    assert ans["classifier"] == "fallback"
    assert ans["decision"]["route"] in ("direct_retrieval", "deliberative_reasoning")
    # the request still completes with a real answer (SC-006)
    assert "299" in ans["answer"]
    st = call(srv, "status")
    assert st["decision_layer"] == "fallback"


def test_recovery_next_request_uses_decision_node(server, monkeypatch):
    """US3 AC2: the moment the backend recovers, the next request is decision-node-served."""
    import agentic_rag_mcp.routing.laya_runtime as rt

    srv, corpus = server
    cfg_holder = srv  # server object; cfg captured in closure — flip via module
    from agentic_rag_mcp.routing import decision as decision_mod

    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: {"answers": {
        "route": {"type": "choice", "choice": "direct_retrieval",
                  "probabilities": {"direct_retrieval": 0.9}},
        "complexity": {"type": "score", "score": 1.5},
        "sufficient": {"type": "noul", "noul": 0.9}}})
    # re-enable on the live config object the server closure reads
    _enable_via = monkeypatch  # noqa: F841
    ans_before = call(srv, "ask", {"question": "What is the speed of light?"})
    assert ans_before["decision"]["provenance"] == "fallback"

    # flip the decider on: server reads cfg.decider_enabled per request
    _cfg = _live_cfg(srv)
    _cfg.decider_enabled = True
    try:
        ans_after = call(srv, "ask", {"question": "What is the speed of light?"})
        assert ans_after["decision"]["provenance"] == "decision_node"
        assert ans_after["classifier"] == "decision_node"
        assert ans_after["decision"]["latency_ms"] >= 0
    finally:
        _cfg.decider_enabled = False


def _live_cfg(server) -> Config:
    """The Config instance the server closure reads (stored on the FastMCP object)."""
    return server._cfg


def test_no_third_provenance_value(server):
    srv, _ = server
    for args in ({"question": "What is the speed of light?"},
                 {"question": "Compare the moon landing and revenue growth", "mode": "deep"}):
        ans = call(srv, "ask", args)
        assert ans["decision"]["provenance"] in ("decision_node", "fallback")


def test_fallback_latency_within_budget(server):
    """SC-006: fallback path completes; latency ceiling asserted in the SC suite."""
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    import time
    t0 = time.perf_counter()
    call(srv, "ask", {"question": "What is the speed of light?"})
    assert (time.perf_counter() - t0) < 10  # generous CI bound; SC-006 measured properly elsewhere


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


_SC006_QUESTIONS = [
    "What is the speed of light?",
    "How fast does light travel in vacuum?",
    "Which city has the largest population?",
    "When did the Apollo landing take place?",
    "What does the review say about customer count?",
    "How many customers are mentioned in the review?",
    "What constant is measured in km per second?",
    "Which document discusses city populations?",
    "What are the highlights of the review?",
    "Where did the astronauts land?",
]
# all questions route "fast" in the heuristic too, so the comparison isolates
# path overhead (mocked decide vs heuristic) rather than route divergence


def test_sc006_fallback_latency_ratio(server, monkeypatch):
    """SC-006 proper: fallback-path median ask latency <= 1.25x primary-path median.
    Interleaved sampling (A/B per question) cancels machine-load drift — the box
    may carry the decision model and Dify while tests run."""
    import time

    import agentic_rag_mcp.routing.laya_runtime as rt

    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: {"answers": {
        "route": {"type": "choice", "choice": "direct_retrieval",
                  "probabilities": {"direct_retrieval": 0.9}},
        "complexity": {"type": "score", "score": 1.5},
        "sufficient": {"type": "noul", "noul": 0.9}}})

    primary, fallback = [], []
    for rep in range(3):
        for q in _SC006_QUESTIONS:
            for enabled, bucket in ((True, primary), (False, fallback)):
                srv._cfg.decider_enabled = enabled
                t0 = time.perf_counter()
                call(srv, "ask", {"question": q})
                bucket.append(time.perf_counter() - t0)
    srv._cfg.decider_enabled = False

    assert _median(fallback) <= 1.25 * _median(primary), (
        f"SC-006 violated: fallback median {_median(fallback):.3f}s "
        f"> 1.25 x primary median {_median(primary):.3f}s")
