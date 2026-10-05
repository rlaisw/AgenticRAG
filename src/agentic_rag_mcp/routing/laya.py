"""Laya decision-layer client (FR-012): delegates System1/System2 routing
to the locally running Laya desktop app; falls back when unreachable."""

from __future__ import annotations

import httpx

from ..errors import DecisionLayerUnavailable


class LayaDecisionLayer:
    def __init__(self, url: str, token: str, timeout: float = 3.0) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def classify(self, question: str) -> str:
        """Returns 'fast' or 'deliberative'. Raises DecisionLayerUnavailable."""
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._url}/classify", json={"question": question}, headers=headers
                )
                resp.raise_for_status()
                label = str(resp.json().get("classification", "")).lower()
        except Exception as exc:  # noqa: BLE001
            raise DecisionLayerUnavailable("laya unreachable") from exc
        if label not in ("fast", "deliberative"):
            raise DecisionLayerUnavailable(f"unexpected classification: {label!r}")
        return label


def heuristic_classify(question: str) -> str:
    """Built-in fallback: keyword/structure heuristic; defaults to deliberative."""
    q = question.lower()
    deep_markers = (
        "compare", " vs ", "analyze", "research", "summarize and",
        "why", "how does", "explain", " and ", " or ",
    )
    if len(q.split()) > 12 or any(m in q for m in deep_markers):
        return "deliberative"
    if q.strip().startswith(("what is", "who is", "when did", "where is")):
        return "fast"
    return "deliberative"
