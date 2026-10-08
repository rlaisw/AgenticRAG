"""US1: one-pass structured routing via the embedded decision node (FR-001..FR-005)."""

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


def direct_output():
    return {"answers": {
        "route": {"type": "choice", "choice": "direct_retrieval",
                  "probabilities": {"direct_retrieval": 0.9, "deliberative_reasoning": 0.06,
                                     "live_web": 0.03, "source_management": 0.01}},
        "complexity": {"type": "score", "score": 1.8},
        "sufficient": {"type": "noul", "noul": 0.94},
    }}


@pytest.fixture()
def server(tmp_path, corpus, monkeypatch):
    import agentic_rag_mcp.routing.laya_runtime as rt

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: direct_output())
    cfg = Config(state_db=tmp_path / "state.sqlite3", vector_dir=tmp_path / "vector",
                 decider_enabled=True, max_iterations=2)
    return build_server(cfg), corpus


def test_direct_route_served_in_one_step(server):
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    ans = call(srv, "ask", {"question": "What is the speed of light?"})
    d = ans["decision"]
    assert d["route"] == "direct_retrieval"
    assert d["provenance"] == "decision_node"
    assert d["complexity"] in (1, 2, 3)          # 1-3 band = simple
    assert d["sufficient"] is True
    assert ans["iterations"] == 0                 # direct path: single retrieval step
    assert ans["classifier"] == "decision_node"
    assert any("physics" in c["title"] for c in ans["citations"])
    assert "299" in ans["answer"]


def test_decision_contains_only_structured_values(server):
    srv, _ = server
    ans = call(srv, "ask", {"question": "What was the quarterly revenue?"})
    d = ans["decision"]
    assert d["route"] in ("direct_retrieval", "deliberative_reasoning", "live_web", "source_management")
    assert isinstance(d["complexity"], int) and 1 <= d["complexity"] <= 10
    assert isinstance(d["sufficient"], bool)
    assert set(d) == {"route", "complexity", "sufficient", "route_probabilities",
                      "provenance", "latency_ms", "valid"}   # no free-text keys


def test_source_management_route_gives_guidance_without_operations(server, monkeypatch):
    import agentic_rag_mcp.routing.laya_runtime as rt
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    before = call(srv, "sources_list")

    out = {"answers": {**direct_output()["answers"],
                       "route": {"type": "choice", "choice": "source_management",
                                 "probabilities": {"source_management": 0.9}}}}
    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: out)
    ans = call(srv, "ask", {"question": "add another documents folder to the sources"})

    assert ans["decision"]["route"] == "source_management"
    assert ans["iterations"] == 0
    assert "sources_" in ans["answer"]            # routing guidance, not an operation
    assert call(srv, "sources_list") == before    # nothing was performed (FR-005)


def test_forced_mode_still_records_decision(server):
    """FR-001: every request passes the decision step; forced mode overrides execution only."""
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    ans = call(srv, "ask", {"question": "What is the speed of light?", "mode": "fast"})
    assert ans["decision"]["provenance"] == "decision_node"
    assert ans["classification"] == "fast"
    assert ans["classifier"] == "forced"
