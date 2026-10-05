"""Polling watcher: change detection feeding the incremental pipeline (US-2)."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

log = logging.getLogger("agentic_rag_mcp.watchers")


class Watcher:
    def __init__(self, pipeline, state, interval_seconds: int = 300) -> None:
        self._pipeline = pipeline
        self._state = state
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def sync_once(self) -> dict:
        results = {}
        for source in self._state.list_sources():
            sid, cfg = source["id"], source["config"]
            try:
                if source["type"] == "local_folder":
                    results[sid] = self._pipeline.sync_local_folder(sid, cfg["path"])
                elif source["type"] == "sqlite":
                    from ..sources.sqlite_source import SqliteSource

                    results[sid] = self._pipeline.sync_sqlite(
                        sid,
                        SqliteSource(cfg["db_path"], cfg["table"], cfg.get("template", "{row}")),
                    )
            except Exception as exc:  # noqa: BLE001 - isolate per-source failures
                self._state.set_health(sid, "degraded", str(exc))
                results[sid] = {"error": str(exc)}
        return results

    def start(self) -> None:
        def loop() -> None:
            while not self._stop.wait(self._interval):
                log.info("periodic sync at %s", datetime.now(timezone.utc))
                self.sync_once()

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
