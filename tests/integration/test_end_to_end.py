"""End-to-end over the in-process FastMCP server: ingest folder + sqlite, ask."""

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
def server(tmp_path, corpus, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = Config(state_db=tmp_path / "state.sqlite3", vector_dir=tmp_path / "vector",
                 laya_url="http://127.0.0.1:1", max_iterations=2)
    return build_server(cfg), corpus


def test_full_flow_ingest_and_ask(server):
    srv, corpus = server
    out = call(srv, "sources_add", {
        "type": "local_folder", "config": {"path": str(corpus["docs"])}})
    stats = out["sync"]
    # 4 valid docs ingested; corrupt pdf skipped with reason
    assert stats["added"] == 4
    assert any("broken.pdf" in s["locator"] for s in stats["skipped"])

    res = call(srv, "search", {"query": "speed of light", "limit": 3})
    assert res and any("physics.pdf" in h["title"] for h in res)

    ans = call(srv, "ask", {"question": "What is the speed of light?", "mode": "fast"})
    assert "299792" in ans["answer"] or "299,792" in ans["answer"]
    assert any("physics" in c["title"] for c in ans["citations"])


def test_incremental_add_update_delete(server, tmp_path):
    srv, corpus = server
    folder = corpus["docs"]
    sid = call(srv, "sources_add", {
        "type": "local_folder", "config": {"path": str(folder)}})["source_id"]

    # add
    (folder / "new.docx").write_bytes(b"")  # empty -> skipped
    from docx import Document
    d = Document(); d.add_paragraph("Pluto was reclassified as a dwarf planet in 2006.")
    d.save(folder / "new.docx")
    stats = call(srv, "sources_sync", {"source_id": sid})[sid]
    assert stats["added"] >= 1

    # delete
    (folder / "physics.pdf").unlink()
    stats = call(srv, "sources_sync", {"source_id": sid})[sid]
    assert stats["deleted"] >= 1
    res = call(srv, "search", {"query": "speed of light"})
    assert all("physics.pdf" != h["title"] for h in res)


def test_deep_path_multi_tool_trace(server):
    srv, corpus = server
    call(srv, "sources_add", {"type": "local_folder",
                                  "config": {"path": str(corpus["docs"])}})
    ans = call(srv, "ask", {
        "question": "Compare the Apollo moon landing and quarterly revenue growth numbers",
        "mode": "deep"})
    assert ans["classification"] == "deliberative"
    assert len(ans["trace"]) >= 1
    assert ans["confidence"] in ("normal", "low")


def test_deep_path_budget_exhaustion_marks_low_confidence(server):
    srv, _corpus = server
    ans = call(srv, "ask", {"question": "What happened on Mars last Tuesday in the office?",
                                "mode": "deep", "max_iterations": 1})
    assert ans["confidence"] == "low"
    assert ans["sufficiency"] == "exhausted"
    assert "citations" in ans
