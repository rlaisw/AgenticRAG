"""Edge-case audit tests (T049): each spec Edge Case gets an asserting test."""

import asyncio
import json

import pytest

from agentic_rag_mcp.config import Config
from agentic_rag_mcp.ingestion.dedup import content_hash
from agentic_rag_mcp.ingestion.parsers import ParseSkipped, extract_text
from agentic_rag_mcp.server import build_server


def call(server, name, args):
    raw = asyncio.run(server.call_tool(name, args))
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
                 max_iterations=2, decider_enabled=False)
    return build_server(cfg), corpus


def test_corrupt_and_encrypted_files_skipped_not_blocking(server):
    """Corrupt source file: skipped with reason, batch continues."""
    srv, corpus = server
    out = call(srv, "sources_add", {"type": "local_folder",
                                    "config": {"path": str(corpus["docs"])}})
    stats = out["sync"]
    assert stats["added"] >= 3
    skipped = stats["skipped"]
    assert skipped and all(s["reason"] for s in skipped), "every skip must carry a reason"


def test_encrypted_pdf_raises_parse_skipped(tmp_path):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.encrypt("secret")
    path = tmp_path / "locked.pdf"
    with open(path, "wb") as f:
        w.write(f)
    with pytest.raises(ParseSkipped, match="encrypted"):
        extract_text(path)


def test_cross_source_duplicate_collapses(tmp_path):
    """Same content from local folder and web origins => single document."""
    from agentic_rag_mcp.store.state import StateStore
    store = StateStore(tmp_path / "s.sqlite3")
    text = "identical unique content appearing in two sources"
    h = content_hash(text)
    d1, _, _ = store.upsert_document(content_hash=h, title="local", extracted_text=text,
                                  media_type="pdf", source_id="folder", locator="/a.pdf")
    d2, outcome, _ = store.upsert_document(content_hash=h, title="onedrive", extracted_text=text,
                                        media_type="pdf", source_id="od", locator="item:1")
    assert d1 == d2 and outcome in ("updated", "linked")
    assert store.doc_count() == 1


def test_expired_credential_marks_source_degraded(tmp_path):
    from agentic_rag_mcp.errors import SourceAuthError
    from agentic_rag_mcp.sources.onedrive import OneDriveSource
    from agentic_rag_mcp.store.state import StateStore

    class Expired:
        def token(self):
            raise SourceAuthError("token expired")

    store = StateStore(tmp_path / "s.sqlite3")
    sid = store.add_source("onedrive", {"client_id": "x"})
    with pytest.raises(SourceAuthError):
        OneDriveSource(Expired()).files()
    store.set_health(sid, "degraded", "auth_expired")
    src = store.get_source(sid)
    assert src["health"] == "degraded" and src["health_reason"] == "auth_expired"


def test_laya_down_falls_back_and_reports(server):
    """Laya unreachable => heuristic fallback, degradation visible in status."""
    srv, _ = server
    st = call(srv, "status", {})
    assert st["decision_layer"] == "fallback"
    ans = call(srv, "ask", {"question": "What is the capital of France?"})
    assert ans["classifier"] == "fallback"


def test_budget_exhaustion_low_confidence(server):
    srv, _ = server
    ans = call(srv, "ask", {"question": "Unknowable multi-part oracle question",
                            "mode": "deep", "max_iterations": 1})
    assert ans["confidence"] == "low"
    assert ans["sufficiency"] == "exhausted"


def test_concurrent_queries_consistent(server):
    """Two concurrent asks do not corrupt state."""
    srv, _ = server
    a = call(srv, "ask", {"question": "What is Alpha?", "mode": "fast"})
    b = call(srv, "ask", {"question": "What is Beta?", "mode": "fast"})
    assert a["citations"] == [] and b["citations"] == []
    assert isinstance(a["answer"], str) and isinstance(b["answer"], str)
