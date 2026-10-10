"""Incremental ingestion pipeline (FR-004): detect add/change/delete,
parse, dedup, embed, upsert into LanceDB, record per-item status.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..errors import RagError
from ..sources.local_folder import LocalFolderSource, ParseSkipped
from .dedup import content_hash

log = logging.getLogger("agentic_rag_mcp.pipeline")


class IngestionPipeline:
    def __init__(self, state, vectors, embedder, collection: str = "default") -> None:
        self.state = state
        self.vectors = vectors
        self.embedder = embedder
        self.collection = collection

    def sync_local_folder(self, source_id: str, folder: str | Path) -> dict:
        src = LocalFolderSource(folder)
        stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": []}
        seen = set()
        for path in src.scan():
            locator = str(path)
            seen.add(locator)
            try:
                text, mtype = src.read_item(path)
            except ParseSkipped as exc:
                stats["skipped"].append({"locator": locator, "reason": str(exc)})
                continue
            except RagError as exc:
                stats["skipped"].append({"locator": locator, "reason": exc.message})
                continue
            doc_id, outcome, orphan_id = self.state.upsert_document(
                content_hash=content_hash(text),
                title=path.name,
                extracted_text=text,
                media_type=mtype,
                source_id=source_id,
                locator=locator,
            )
            count = self.vectors.upsert_document(
                collection=self.collection,
                document_id=doc_id,
                title=path.name,
                text=text,
                embedder=self.embedder,
            )
            if orphan_id:  # evicted by a content change — drop its stale chunks
                self.vectors.delete_document(self.collection, orphan_id)
            if outcome == "created":
                stats["added"] += 1
            elif outcome == "updated":
                stats["updated"] += 1
            log.info("ingested %s (%s chunks)", locator, count)
        # deletions: origins under this source not seen this cycle
        existing = self.state.get_source(source_id)
        prev = set((existing or {}).get("sync_state", {}).get("locators", []))
        for stale in prev - seen:
            doc = self.state.remove_origin(source_id, stale)
            if doc:
                self.vectors.delete_document(self.collection, doc)
            stats["deleted"] += 1
        self.state.set_sync_state(source_id, {"locators": sorted(seen)})
        self.state.set_health(source_id, "healthy", None)
        return stats

    def sync_onedrive(self, source_id: str, source) -> dict:
        """Sync a OneDrive source: delta → download → parse → embed (FR-005..FR-014).

        `source` is an OneDriveSource instance with a .sync(state) method that
        returns {added, updated, deleted, skipped, delta_link}. The pipeline
        ingests new/changed files and evicts deleted ones (spec-002 eviction).
        """
        existing = self.state.get_source(source_id) or {}
        prev_state = existing.get("sync_state", {})
        result = source.sync(state=prev_state)

        stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": result["skipped"]}
        for entry in result["added"] + result["updated"]:
            try:
                text = entry["content"].decode("utf-8", errors="replace")
            except Exception:
                text = str(entry["content"])
            doc_id, outcome = self.state.upsert_document(
                content_hash=content_hash(text),
                title=entry["title"],
                extracted_text=text,
                media_type=entry.get("media_type", "onedrive"),
                source_id=source_id,
                locator=entry["locator"],
            )
            self.vectors.upsert_document(
                collection=self.collection,
                document_id=doc_id,
                title=entry["title"],
                text=text,
                embedder=self.embedder,
            )
            if outcome == "created":
                stats["added"] += 1
            else:
                stats["updated"] += 1

        for removed in result["deleted"]:
            doc = self.state.remove_origin(source_id, removed["locator"])
            if doc:
                self.vectors.delete_document(self.collection, doc)
            stats["deleted"] += 1

        # persist delta-link cursor for the next incremental sync (FR-009)
        self.state.set_sync_state(source_id, {"delta_link": result["delta_link"]})
        self.state.set_health(source_id, "healthy", None)
        return stats

    def sync_sqlite(self, source_id: str, source) -> dict:
        stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": []}
        seen = set()
        for row in source.rows():
            seen.add(row["locator"])
            doc_id, outcome, orphan_id = self.state.upsert_document(
                content_hash=row["hash"],
                title=row["title"],
                extracted_text=row["text"],
                media_type="sqlite_record",
                source_id=source_id,
                locator=row["locator"],
            )
            self.vectors.upsert_document(
                collection=self.collection,
                document_id=doc_id,
                title=row["title"],
                text=row["text"],
                embedder=self.embedder,
            )
            if orphan_id:  # evicted by a content change — drop its stale chunks
                self.vectors.delete_document(self.collection, orphan_id)
            if outcome == "created":
                stats["added"] += 1
            elif outcome == "updated":
                stats["updated"] += 1
        existing = self.state.get_source(source_id)
        prev = set((existing or {}).get("sync_state", {}).get("locators", []))
        for stale in prev - seen:
            doc = self.state.remove_origin(source_id, stale)
            if doc:
                self.vectors.delete_document(self.collection, doc)
            stats["deleted"] += 1
        self.state.set_sync_state(source_id, {"locators": sorted(seen)})
        self.state.set_health(source_id, "healthy", None)
        return stats
