"""Graphify semantic-search wrapper (FR-010, optional layer).

Talks to the graphify CLI over a built graph (`graphify-out/graph.json`).
Disabled by default — callers get FeatureDisabledError until enabled and a
graph is built (`graphify .`, or swap the graph path in config).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ..errors import FeatureDisabledError, NotFoundError, ProviderError


class GraphifySearch:
    def __init__(self, graph_path: Path, enabled: bool = False) -> None:
        self.graph_path = Path(graph_path)
        self.enabled = enabled

    def _require_ready(self) -> None:
        if not self.enabled:
            raise FeatureDisabledError("graphify layer disabled; enable in config.features")
        if shutil.which("graphify") is None:
            raise ProviderError("graphify CLI not installed")
        if not self.graph_path.exists():
            raise NotFoundError(
                f"graph not built: {self.graph_path} (run `graphify .` in the project)")

    def _run(self, *args: str, timeout: float = 30.0) -> str:
        self._require_ready()
        try:
            proc = subprocess.run(
                ["graphify", *args, "--graph", str(self.graph_path)],
                capture_output=True, text=True, timeout=timeout, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError("graphify timed out") from exc
        if proc.returncode != 0:
            raise ProviderError(f"graphify failed: {proc.stderr.strip()[:200]}")
        return proc.stdout

    def explain(self, node: str) -> dict:
        """Plain-language explanation of a node and its neighbours."""
        return {"answer": self._run("explain", node), "nodes": [], "edges": []}

    def path(self, source: str, target: str) -> dict:
        """Shortest path between two graph nodes."""
        return {"answer": self._run("path", source, target), "nodes": [], "edges": []}

    def stats(self) -> dict:
        """Node/edge counts, read directly from graph.json."""
        self._require_ready()
        data = json.loads(self.graph_path.read_text())
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        return {"nodes": len(nodes), "edges": len(edges), "graph": str(self.graph_path)}
