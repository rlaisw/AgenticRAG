"""Sufficiency evaluation node (FR-014/FR-017)."""

from __future__ import annotations

MIN_HITS = 2


def assess(question: str, hits: list[dict], started: int, budget: int) -> dict:
    """Returns {'outcome': 'satisfied'|'continue'|'exhausted', 'reason': str}."""
    if len(hits) >= MIN_HITS and all(h.get("snippet") or h.get("content") for h in hits[:MIN_HITS]):
        return {"outcome": "satisfied", "reason": f"{len(hits)} supported hits"}
    if started + 1 >= budget:
        return {"outcome": "exhausted", "reason": "iteration budget reached"}
    return {"outcome": "continue", "reason": f"only {len(hits)} hits"}
