"""Outage-only fallback router (FR-003): keyword heuristic, provenance "fallback"."""

from __future__ import annotations

def heuristic_classify(question: str) -> str:
    """Built-in fallback: keyword/structure heuristic.

    Simple question openers route fast (SC-006 outage-latency parity);
    markers, conjunctions, and long questions stay deliberative (safe default).
    """
    q = question.lower()
    deep_markers = (
        "compare", " vs ", "analyze", "research", "summarize and",
        "why", "how does", "explain", " and ", " or ",
    )
    if len(q.split()) > 12 or any(m in q for m in deep_markers):
        return "deliberative"
    if q.strip().startswith(("what", "who", "when", "where", "which",
                             "how many", "how much", "how fast", "how long")):
        return "fast"
    return "deliberative"
