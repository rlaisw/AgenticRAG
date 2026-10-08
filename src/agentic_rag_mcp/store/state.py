"""SQLite state store: documents, origins, sources, sessions.

Dedup rule (FR-006): documents.content_hash is UNIQUE across the corpus.
Deletion rule: a Document is dropped only when its LAST OriginRef is removed.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    media_type TEXT NOT NULL CHECK (
        media_type IN ('pdf','docx','xlsx','pptx','audio','sqlite_record','web')
    ),
    status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','failed','skipped')),
    status_reason TEXT,
    ingested_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS origins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL,
    locator TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE (source_id, locator)
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN (
        'local_folder','sqlite','onedrive','sharepoint','web_tavily','web_exa','web_searxng'
    )),
    config TEXT NOT NULL,
    credentials_ref TEXT,
    sync_state TEXT NOT NULL DEFAULT '{}',
    health TEXT NOT NULL DEFAULT 'healthy' CHECK (health IN ('healthy','degraded','down')),
    health_reason TEXT,
    last_sync_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    classification TEXT,
    classifier TEXT,
    plan TEXT,
    iterations INTEGER NOT NULL DEFAULT 0,
    sufficiency TEXT,
    answer TEXT,
    confidence TEXT NOT NULL DEFAULT 'normal',
    citations TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- documents / origins -------------------------------------------

    def upsert_document(
        self,
        *,
        content_hash: str,
        title: str,
        extracted_text: str,
        media_type: str,
        source_id: str,
        locator: str,
    ) -> tuple[str, str]:
        """Returns (document_id, outcome, orphan_id): outcome is created|updated
        (updated = content seen before, or content changed at an existing origin);
        orphan_id is the previous document evicted when a locator's content changed
        and the old document lost its last origin — the caller must drop its vectors."""
        now = _now()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, content_hash FROM documents WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            if row:
                doc_id = row["id"]
                conn.execute(
                    "UPDATE documents SET extracted_text = ?, title = ?, updated_at = ?"
                    " WHERE id = ?",
                    (extracted_text, title, now, doc_id),
                )
                outcome = "updated"
            else:
                doc_id = uuid.uuid4().hex
                conn.execute(
                    "INSERT INTO documents (id, content_hash, title, extracted_text, media_type,"
                    " ingested_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                    (doc_id, content_hash, title, extracted_text, media_type, now, now),
                )
                outcome = "created"
            linked = conn.execute(
                "UPDATE origins SET last_seen_at = ? WHERE source_id = ? AND locator = ?",
                (now, source_id, locator),
            ).rowcount
            orphan_id = None
            prev = conn.execute(
                "SELECT document_id FROM origins WHERE source_id = ? AND locator = ?",
                (source_id, locator),
            ).fetchone()
            if prev and prev["document_id"] != doc_id:
                # content changed at this locator: re-point the origin, evict the
                # old document if it lost its last origin (bug fix — old chunks
                # previously lingered in the vector store as stale results)
                old_id = prev["document_id"]
                conn.execute(
                    "UPDATE origins SET document_id = ?, last_seen_at = ?"
                    " WHERE source_id = ? AND locator = ?",
                    (doc_id, now, source_id, locator),
                )
                remaining = conn.execute(
                    "SELECT COUNT(*) AS n FROM origins WHERE document_id = ?", (old_id,)
                ).fetchone()["n"]
                if remaining == 0:
                    conn.execute("DELETE FROM documents WHERE id = ?", (old_id,))
                    orphan_id = old_id
                outcome = "updated"
            elif not linked:
                conn.execute(
                    "INSERT INTO origins (document_id, source_id, locator, last_seen_at)"
                    " VALUES (?,?,?,?)",
                    (doc_id, source_id, locator, now),
                )
            return doc_id, outcome, orphan_id

    def remove_origin(self, source_id: str, locator: str) -> str | None:
        """Remove an origin; returns document_id if the document was fully removed."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT document_id FROM origins WHERE source_id = ? AND locator = ?",
                (source_id, locator),
            ).fetchone()
            if not row:
                return None
            doc_id = row["document_id"]
            conn.execute(
                "DELETE FROM origins WHERE source_id = ? AND locator = ?", (source_id, locator)
            )
            remaining = conn.execute(
                "SELECT COUNT(*) AS n FROM origins WHERE document_id = ?", (doc_id,)
            ).fetchone()["n"]
            if remaining == 0:
                conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                return doc_id
            return None

    def get_document(self, doc_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            return dict(row) if row else None

    def doc_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) AS n FROM documents WHERE status='ok'").fetchone()[
                "n"
            ]

    # ---- sources --------------------------------------------------------

    def add_source(
        self, source_type: str, config: dict, credentials_ref: str | None = None
    ) -> str:
        source_id = uuid.uuid4().hex[:12]
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sources (id, type, config, credentials_ref) VALUES (?,?,?,?)",
                (source_id, source_type, json.dumps(config), credentials_ref),
            )
        return source_id

    def get_source(self, source_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
            if not row:
                return None
            out = dict(row)
            out["config"] = json.loads(out["config"])
            out["sync_state"] = json.loads(out["sync_state"])
            return out

    def list_sources(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY type, id").fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["config"] = json.loads(d["config"])
                d["sync_state"] = json.loads(d["sync_state"])
                out.append(d)
            return out

    def remove_source(self, source_id: str) -> list[str]:
        """Remove a source and all its origins; returns deleted document ids."""
        with self._conn() as conn:
            locators = conn.execute(
                "SELECT locator FROM origins WHERE source_id = ?", (source_id,)
            ).fetchall()
            deleted = []
            for r in locators:
                doc = self.remove_origin(source_id, r["locator"])
                if doc:
                    deleted.append(doc)
            conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            return deleted

    def set_health(self, source_id: str, health: str, reason: str | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sources SET health = ?, health_reason = ? WHERE id = ?",
                (health, reason, source_id),
            )

    def set_sync_state(self, source_id: str, state: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sources SET sync_state = ?, last_sync_at = ? WHERE id = ?",
                (json.dumps(state), _now(), source_id),
            )

    # ---- sessions -------------------------------------------------------

    def save_session(self, session: dict) -> str:
        sid = uuid.uuid4().hex
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, question, classification, classifier, plan,"
                " iterations, sufficiency, answer, confidence, citations, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    sid,
                    session["question"],
                    session.get("classification"),
                    session.get("classifier"),
                    json.dumps(session.get("plan", [])),
                    session.get("iterations", 0),
                    session.get("sufficiency"),
                    session.get("answer"),
                    session.get("confidence", "normal"),
                    json.dumps(session.get("citations", [])),
                    _now(),
                ),
            )
        return sid
