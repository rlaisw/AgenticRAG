"""Agent tool bindings (FR-013/FR-015): vector_search, sql_query, web_search,

graphify. Each tool returns list[dict] hits; failures are contained per-tool.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def make_vector_tool(vector_store, embedder, collection: str = "default"):
    def vector_search(query: str, limit: int = 5) -> list[dict]:
        return vector_store.search(collection, embedder([query])[0], limit=limit)

    return vector_search


def make_sql_tool(db_path: str | Path, table: str, text_column: str | None = None):
    def sql_query(query: str, limit: int = 5) -> list[dict]:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            like = f"%{query.split()[0][:40]}%"
            col = text_column or "1=1"
            if text_column:
                rows = conn.execute(
                    f"SELECT rowid, * FROM {table} WHERE {text_column} LIKE ? LIMIT ?",
                    (like, limit),
                ).fetchall()
            else:
                rows = conn.execute(f"SELECT rowid, * FROM {table} LIMIT ?", (limit,)).fetchall()
            cols = [d[1] for d in conn.execute(f"PRAGMA table_info({table})")]
            return [
                {
                    "content": " | ".join(str(v) for v in dict(zip(cols, row[1:])).values()),
                    "document_id": f"sqlite:{table}:{row[0]}",
                    "title": f"{table} row {row[0]}",
                }
                for row in rows
            ]
        finally:
            conn.close()

    return sql_query


def make_web_tool(providers: list):
    def web_search(query: str, limit: int = 5) -> list[dict]:
        for provider in providers:
            try:
                hits = provider.search(query, limit=limit)
                if hits:
                    return hits
            except Exception:  # noqa: BLE001 - fall through to next provider
                continue
        return []

    return web_search
