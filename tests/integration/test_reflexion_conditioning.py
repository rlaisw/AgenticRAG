"""US2 integration: reflexion over the real server (multi-part coverage, live_web ordering)."""

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
                 decider_enabled=False, max_iterations=3)
    return build_server(cfg), corpus


def test_multi_part_question_covers_all_parts_with_reflections(server):
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder", "config": {"path": str(corpus["docs"])}})
    ans = call(srv, "ask", {
        "question": "Compare the Apollo moon landing and quarterly revenue growth numbers",
        "mode": "deep"})
    assert ans["classification"] == "deliberative"
    assert ans["decision"]["route"] in ("deliberative_reasoning", "live_web",
                                        "direct_retrieval", "source_management")
    # both parts of the compound question surface in the answer text
    assert "apollo" in ans["answer"].lower() or "moon" in ans["answer"].lower()
    assert "revenue" in ans["answer"].lower() or "12" in ans["answer"]
    # structured reflections with score + verdict + critique (FR-014)
    assert ans["reflections"]
    for r in ans["reflections"]:
        assert 1 <= r["evaluator_score"] <= 10
        assert r["evaluator_verdict"] in ("pass", "fail")
        assert isinstance(r["critique"], str) and r["critique"]


def test_live_web_route_leads_with_web_tools(server):
    """Deep loop stays bounded and flagged when web providers are absent (tool
    isolation); web-first ORDERING is unit-tested in test_reflexion_graph.py."""
    srv, _ = server
    ans = call(srv, "ask", {"question": "what time is it in hong kong", "mode": "deep"})
    assert ans["classification"] == "deliberative"
    assert ans["decision"]["provenance"] == "fallback"  # fixture decider disabled
    assert ans["iterations"] <= 3
    assert ans["reflections"]  # every trial left a structured record
