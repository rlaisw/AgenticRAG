"""contracts/ask-response.md: preserved fields under BOTH provenance values (FR-015, SC-007)."""

import asyncio
import json

import pytest

from agentic_rag_mcp.config import Config
from agentic_rag_mcp.server import build_server

PRESERVED = ("answer", "confidence", "classification", "iterations", "sufficiency",
             "trace", "citations", "error", "plan")
NEW = ("decision", "reflections")


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
                 decider_enabled=False, max_iterations=2)
    return build_server(cfg), corpus


@pytest.mark.parametrize("mode", ["fast", "deep"])
def test_all_fields_present_on_every_response(server, mode):
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    for question in ("What is the speed of light?",
                     "Compare the moon landing and the revenue growth"):
        ans = call(srv, "ask", {"question": question, "mode": mode})
        for field in PRESERVED:
            assert field in ans, f"preserved field missing: {field} (mode={mode})"
        for field in NEW:
            assert field in ans, f"new field missing: {field}"


def test_decision_invariants_on_both_provenances(server, monkeypatch):
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})

    # fallback provenance (decider disabled in fixture)
    ans_fb = call(srv, "ask", {"question": "What is the speed of light?"})
    assert ans_fb["decision"]["provenance"] == "fallback"

    # decision_node provenance (mock the model, flip the live config)
    import agentic_rag_mcp.routing.laya_runtime as rt

    monkeypatch.setattr(rt, "system_one", lambda cfg, s, q: {"answers": {
        "route": {"type": "choice", "choice": "deliberative_reasoning",
                  "probabilities": {"deliberative_reasoning": 0.9}},
        "complexity": {"type": "score", "score": 7.2},
        "sufficient": {"type": "noul", "noul": 0.4}}})
    srv._cfg.decider_enabled = True
    try:
        ans_dn = call(srv, "ask", {"question": "Compare the moon landing and revenue growth"})
        d = ans_dn["decision"]
        assert d["provenance"] == "decision_node"
        assert d["route"] == "deliberative_reasoning"
        assert d["complexity"] == 7                       # in 1-10 (FR-002)
        assert ans_dn["classification"] == "deliberative"
        # deliberative responses carry per-iteration verdicts + critiques (FR-014)
        assert ans_dn["reflections"]
        for r in ans_dn["reflections"]:
            assert 1 <= r["evaluator_score"] <= 10
            assert r["evaluator_verdict"] in ("pass", "fail")
    finally:
        srv._cfg.decider_enabled = False
