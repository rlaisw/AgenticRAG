"""Rule-based Evaluator (FR-007, FR-010; research.md D5).

Score + binary verdict for every draft; the sufficiency hit-count floor
(agents/sufficiency.py) is a scoring INPUT here — not a gate elsewhere (FR-010).
Deterministic: identical inputs produce identical outputs.
"""

from __future__ import annotations

import re

from .sufficiency import MIN_HITS

# ponytail: tuned constants; make config-driven if they ever need tuning.
# MIN_COVERAGE 0.8 aligns the pass gate with SC-004's >=80% multi-part coverage target (T032).
MIN_COVERAGE = 0.8

_STOP = frozenset(
    "what when where which who whom how why is are was were the a an in of to on for "
    "and or vs did does do done can could should would will time it its this that "
    "with about there their them they your you tell compare numbers".split()
)


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(w) > 2 and w not in _STOP}


def evaluate(question: str, draft: str, evidence: list[dict]) -> tuple[int, str, list[str]]:
    """Returns (score 1-10, verdict "pass"|"fail", missing question terms)."""
    q_terms = _terms(question)
    d_terms = set(re.findall(r"[a-z0-9]+", (draft or "").lower()))
    missing_all = q_terms - d_terms
    missing = sorted(missing_all)[:6]
    coverage = 1.0 if not q_terms else (len(q_terms) - len(missing_all)) / len(q_terms)
    citable = any(h.get("document_id") or h.get("url") for h in evidence)
    # FR-010: hit count is a scoring input, not a verdict gate
    hit_factor = min(1.0, len(evidence) / MIN_HITS)
    score = int(10 * coverage * hit_factor * (0.5 if not citable else 1.0))
    score = max(1, min(10, score))
    verdict = "pass" if (coverage >= MIN_COVERAGE and citable) else "fail"
    return score, verdict, missing
