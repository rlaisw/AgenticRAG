from agentic_rag_mcp.ingestion.dedup import content_hash


def test_same_content_one_document(tmp_path):
    """FR-006: identical content from two locators dedups to one document."""
    from agentic_rag_mcp.store.state import StateStore

    store = StateStore(tmp_path / "s.sqlite3")
    h = content_hash("The quick brown fox")
    d1, out1, _ = store.upsert_document(
        content_hash=h, title="a.txt", extracted_text="The quick brown fox",
        media_type="pdf", source_id="s1", locator="/a")
    d2, out2, _ = store.upsert_document(
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
    doc, _, _ = store.upsert_document(content_hash=h, title="a", extracted_text="x",
                                   media_type="pdf", source_id="s1", locator="/a")
    store.upsert_document(content_hash=h, title="b", extracted_text="x",
                          media_type="pdf", source_id="s2", locator="/b")
    assert store.remove_origin("s1", "/a") is None  # still linked via s2
    assert store.doc_count() == 1
    assert store.remove_origin("s2", "/b") == doc  # last origin removed -> dropped
    assert store.doc_count() == 0


def test_changed_content_repoints_origin_and_evicts_old_doc(tmp_path):
    """A file's edited content must replace (not duplicate) the old document:
    the origin re-points to the new doc, the old doc is dropped and returned
    as an orphan so its stale chunks can be deleted."""
    from agentic_rag_mcp.store.state import StateStore

    store = StateStore(tmp_path / "s.sqlite3")
    v1, out1, orphan1 = store.upsert_document(
        content_hash=content_hash("revenue was 100"), title="r.docx",
        extracted_text="revenue was 100", media_type="docx",
        source_id="s1", locator="/r")
    assert (out1, orphan1) == ("created", None)

    v2, out2, orphan2 = store.upsert_document(
        content_hash=content_hash("revenue was 999"), title="r.docx",
        extracted_text="revenue was 999", media_type="docx",
        source_id="s1", locator="/r")  # same locator, new content
    assert v2 != v1
    assert out2 == "updated"
    assert orphan2 == v1            # old doc evicted, caller must drop its vectors
    assert store.doc_count() == 1   # no duplicate docs


def test_changed_content_keeps_old_doc_while_other_origin_remains(tmp_path):
    """If the old content still exists at another source, it must survive."""
    from agentic_rag_mcp.store.state import StateStore

    store = StateStore(tmp_path / "s.sqlite3")
    h = content_hash("shared text")
    v1, _, _ = store.upsert_document(content_hash=h, title="a", extracted_text="shared text",
                                     media_type="docx", source_id="s1", locator="/a")
    store.upsert_document(content_hash=h, title="b", extracted_text="shared text",
                          media_type="docx", source_id="s2", locator="/b")
    _, out, orphan = store.upsert_document(
        content_hash=content_hash("new text"), title="a", extracted_text="new text",
        media_type="docx", source_id="s1", locator="/a")
    assert out == "updated"
    assert orphan is None            # old doc still linked via /b — not evicted
    assert store.doc_count() == 2
