"""Read-only SQLite data source (FR-002). Row -> text template, per-row hashes."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from ..errors import NotFoundError


class SqliteSource:
    type = "sqlite"

    def __init__(self, db_path: str, table: str, template: str = "{row}") -> None:
        path = Path(db_path).expanduser()
        if not path.is_file():
            raise NotFoundError(f"sqlite db not found: {path}")
        self.db_path = path
        self.table = table
        self.template = template

    def rows(self) -> list[dict]:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({self.table})")]
            out = []
            for row in conn.execute(f"SELECT rowid AS _rid, * FROM {self.table}"):
                d = {c: row[c] for c in cols}
                text = self.template.format(row=d) if self.template != "{row}" else " | ".join(
                    f"{k}={v}" for k, v in d.items()
                )
                out.append(
                    {
                        "locator": f"{self.table}:{row['_rid']}",
                        "title": f"{self.table} row {row['_rid']}",
                        "text": text,
                        "hash": hashlib.sha256(text.encode()).hexdigest(),
                    }
                )
            return out
        finally:
            conn.close()
