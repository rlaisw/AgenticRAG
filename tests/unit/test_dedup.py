from agentic_rag_mcp.ingestion.dedup import content_hash


def test_same_content_one_document(tmp_path):
    """FR-006: identical content from two locators dedups to one document."""
    from agentic_rag_mcp.store.state import StateStore

    store = StateStore(tmp_path / "s.sqlite3")
    h = content_hash("The quick brown fox")
    d1, out1 = store.upsert_document(
        content_hash=h, title="a.txt", extracted_text="The quick brown fox",
        media_type="pdf", source_id="s1", locator="/a")
    d2, out2 = store.upsert_document(
        content_hash=h, title="b.txt", extracted_text="The quick brown fox",
        media_type="pdf", source_id="s2", locator="/b")
    assert d1 == d2 and out1 == "created" and out2 == "updated"
    assert store.doc_count() == 1


def test_normalized_hash_ignores_whitespace():
    assert content_hash("hello   world") == content_hash("HELLO world")


def test_document_dropped_only_when_last_origin_removed(tmp_path):
    from agentic_rag_mcp.store.state import StateStore

    store = StateStore(tmp_path / "s.sqlite3")
    h = content_hash("shared content")
    doc, _ = store.upsert_document(content_hash=h, title="a", extracted_text="x",
                                   media_type="pdf", source_id="s1", locator="/a")
    store.upsert_document(content_hash=h, title="b", extracted_text="x",
                          media_type="pdf", source_id="s2", locator="/b")
    assert store.remove_origin("s1", "/a") is None  # still linked via s2
    assert store.doc_count() == 1
    assert store.remove_origin("s2", "/b") == doc  # last origin removed -> dropped
    assert store.doc_count() == 0
