"""Contract tests: realistic failure modes reconciliation with contracts/mcp-tools.md."""

import asyncio

import pytest

from agentic_rag_mcp.config import Config
from agentic_rag_mcp.server import build_server


def call(server, name, args):
    import json
    raw = asyncio.run(server.call_tool(name, args))
    # FastMCP v1 returns a list mixing text blocks and structured results
    structured = [b["result"] for b in raw if isinstance(b, dict) and "result" in b]
    if structured:
        return structured[0]
    texts = [getattr(b, "text", "") for b in raw if getattr(b, "text", "")]
    joined = "".join(texts).strip()
    return json.loads(joined) if joined else None


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))  # isolate config/state dirs
    cfg = Config(state_db=tmp_path / "state.sqlite3", vector_dir=tmp_path / "vector",
                 decider_enabled=False)
    return build_server(cfg)


def test_ask_no_documents_returns_no_fabrication(server):
    out = call(server, "ask", {"question": "What is the airspeed of a swallow?"})
    assert "answer" in out
    assert out["answer"].startswith("No relevant information") or "could not" in out["answer"]
    assert out["citations"] == []


def test_unknown_source_remove_is_graceful(server):
    out = call(server, "sources_remove", {"source_id": "zz"})
    assert out == {"removed": "zz", "documents_deleted": 0}


def test_bad_source_type_raises_not_found(server):
    with pytest.raises(Exception) as ei:  # FastMCP wraps tool errors
        call(server, "sources_add", {"type": "gopher", "config": {}})
    assert "unsupported source type" in str(ei.value)


def test_graph_query_disabled_by_default(server):
    with pytest.raises(Exception) as ei:
        call(server, "graph_query", {"query": "x"})
    assert "FeatureDisabled" in str(ei.value) or "disabled" in str(ei.value)


def test_status_shape(server):
    out = call(server, "status", {})
    assert out["decision_layer"] in ("decision_node", "fallback")
    assert "index" in out and "sources" in out
    assert "documents" in out["index"] and "chunks" in out["index"]
