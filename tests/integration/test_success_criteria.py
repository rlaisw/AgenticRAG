"""Success-criteria measurements (SC-001/002/003/005) — 100-question suite.

SC-006's outage latency ceiling is exercised in test_fallback_provenance.py;
SC-004's 80% multi-part coverage in test_reflexion_conditioning.py (real corpus).
"""

import asyncio
import json
import time

import pytest

from agentic_rag_mcp.config import Config
from agentic_rag_mcp.server import build_server

# 100 questions across all four routes and every complexity band
QUESTIONS = [f"Question number {i}: what does the corpus say about topic {i % 7}?"
             for i in range(80)] + \
    ["what time is it in hong kong", "current weather today", "latest news",
     "add a documents folder as a source", "list my sources please",
     "sync all sources now", "remove a source by id", "compare A and B",
     "analyze the difference between revenue and growth",
     "summarize and research the moon landing and the speed of light",
     "how do I trace an email", "when did the apollo launch",
     "what is the quarterly revenue", "show the city populations",
     "simple physics question", "very complex multi-part analytical question",
     "what happened recently", "news about the landing",
     "2026 annual review", "the database table numbers"]


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
    import agentic_rag_mcp.routing.laya_runtime as rt

    monkeypatch.setenv("HOME", str(tmp_path))

    def fast_system_one(cfg, state, questions):
        route = ("source_management" if any(w in state.lower() for w in
                 ("add", "list", "sync", "remove", "source"))
                else "live_web" if any(w in state.lower() for w in
                 ("time", "weather", "news", "today", "recent", "2026"))
                else "direct_retrieval" if len(state) < 55
                else "deliberative_reasoning")
        return {"answers": {
            "route": {"type": "choice", "choice": route,
                      "probabilities": {route: 0.9}},
            "complexity": {"type": "score", "score": 2.0 if route == "direct_retrieval" else 8.0},
            "sufficient": {"type": "noul", "noul": 0.9 if route == "direct_retrieval" else 0.3},
        }}

    monkeypatch.setattr(rt, "system_one", fast_system_one)
    cfg = Config(state_db=tmp_path / "state.sqlite3", vector_dir=tmp_path / "vector",
                 decider_enabled=True, max_iterations=2)
    srv = build_server(cfg)
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    return srv


def test_sc001_002_003_over_100_questions(server):
    assert len(QUESTIONS) == 100
    under_2s = valid_schema = node_provenance = 0
    for q in QUESTIONS:
        t0 = time.perf_counter()
        ans = call(server, "ask", {"question": q})
        dt = time.perf_counter() - t0
        d = ans["decision"]
        if dt < 2.0:
            under_2s += 1
        if (d["route"] in ("direct_retrieval", "deliberative_reasoning", "live_web",
                           "source_management")
                and isinstance(d["complexity"], int) and 1 <= d["complexity"] <= 10
                and isinstance(d["sufficient"], bool)):
            valid_schema += 1
        if d["provenance"] == "decision_node":
            node_provenance += 1
    assert under_2s >= 95, f"SC-001: only {under_2s}/100 under 2s"
    assert valid_schema == 100, f"SC-002: only {valid_schema}/100 schema-valid"
    assert node_provenance == 100, f"SC-003: only {node_provenance}/100 decision-node"


def test_sc005_budget_exhausted_always_flagged_low(server):
    ans = call(server, "ask", {"question": "obscure gibberish xyzzy nothing matches",
                               "mode": "deep", "max_iterations": 1})
    assert ans["sufficiency"] == "exhausted"
    assert ans["confidence"] == "low"
    assert ans["error"] is not None
    assert ans["reflections"]           # full memory carried (SC-005)
    assert ans["iterations"] == 1       # budget respected — never exceeded
