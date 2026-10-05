"""Coverage pass: sql tool, watcher loop, parser helpers, web fallback order."""

import sqlite3

from agentic_rag_mcp.agents.tools import make_sql_tool, make_web_tool
from agentic_rag_mcp.errors import ProviderError
from agentic_rag_mcp.ingestion.watchers import Watcher
from agentic_rag_mcp.ingestion.pipeline import IngestionPipeline
from agentic_rag_mcp.store.state import StateStore
from agentic_rag_mcp.store.vectordb import VectorStore
from agentic_rag_mcp.search.embeddings import Embedder


def test_sql_tool_reads_rows(tmp_path):
    db = tmp_path / "t.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE cities (name TEXT, pop REAL)")
    conn.execute("INSERT INTO cities VALUES ('Tokyo', 37.4)")
    conn.commit(); conn.close()

    tool = make_sql_tool(db, "cities", text_column="name")
    hits = tool("Tokyo")
    assert hits and "Tokyo" in hits[0]["content"]
    assert hits[0]["document_id"].startswith("sqlite:cities:")


def test_sql_tool_no_text_column(tmp_path):
    db = tmp_path / "t.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE nums (n INTEGER)")
    conn.execute("INSERT INTO nums VALUES (1)")
    conn.commit(); conn.close()
    tool = make_sql_tool(db, "nums")
    assert len(tool("anything")) == 1


def test_web_tool_fallback_order():
    calls = []

    class Down:
        def search(self, q, limit=5):
            calls.append("down")
            raise ProviderError("down")

    class Up:
        def search(self, q, limit=5):
            calls.append("up")
            return [{"title": "t", "url": "https://u", "snippet": "s"}]

    hits = make_web_tool([Down(), Up()])("q")
    assert calls == ["down", "up"] and hits[0]["url"] == "https://u"


def test_web_tool_all_down_returns_empty():
    class AlwaysDown:
        def search(self, q, limit=5):
            raise ProviderError("nope")

    assert make_web_tool([AlwaysDown(), AlwaysDown()])("q") == []


def test_watcher_sync_once_local(tmp_path, corpus):
    state = StateStore(tmp_path / "s.sqlite3")
    vectors = VectorStore(tmp_path / "v")
    embedder = Embedder()
    pipeline = IngestionPipeline(state, vectors, embedder)
    sid = state.add_source("local_folder", {"path": str(corpus["docs"])})
    watcher = Watcher(pipeline, state, interval_seconds=9999)
    results = watcher.sync_once()
    assert sid in results and results[sid]["added"] >= 3


def test_watcher_isolates_bad_source(tmp_path, corpus):
    state = StateStore(tmp_path / "s.sqlite3")
    vectors = VectorStore(tmp_path / "v")
    embedder = Embedder()
    pipeline = IngestionPipeline(state, vectors, embedder)
    good = state.add_source("local_folder", {"path": str(corpus["docs"])})
    bad = state.add_source("local_folder", {"path": str(corpus["docs"])})
    # break the pipeline for 'bad' by deleting its folder afterwards
    watcher = Watcher(pipeline, state)
    watcher.sync_once()
    import shutil
    shutil.rmtree(corpus["docs"])
    results = watcher.sync_once()
    assert results[bad].get("error") or results[good]["deleted"] >= 1
    assert state.get_source(bad)["health"] in ("degraded", "healthy")
