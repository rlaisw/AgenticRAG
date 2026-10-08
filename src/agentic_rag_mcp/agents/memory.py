"""Episodic memory + reflection records for the System 2 reflexion graph.

Per-request lifecycle (FR-012): created empty at request start, appended by the
Self-Reflector stage, read by the Actor stage, discarded when the request
completes. Full history conditions every subsequent trial (FR-009).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReflectionRecord:
    """One reflexion cycle's outcome (data-model.md)."""

    iteration: int                      # 1-based trial number
    evaluator_score: int                # rule-based quality score, 1-10
    evaluator_verdict: str              # "pass" | "fail"
    critique: str                       # verbal critique of the specific failure
    missing_focus: list[str] = field(default_factory=list)  # shortfalls to target next trial

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "evaluator_score": self.evaluator_score,
            "evaluator_verdict": self.evaluator_verdict,
            "critique": self.critique,
            "missing_focus": self.missing_focus,
        }


class EpisodicMemory:
    """Ordered per-request buffer of ReflectionRecords."""

    def __init__(self) -> None:
        self._records: list[ReflectionRecord] = []

    def append(self, record: ReflectionRecord) -> None:
        self._records.append(record)

    def union_missing_focus(self) -> list[str]:
        """Union of missing-focus terms across ALL records, order of first
        appearance — the full history conditions each subsequent trial (FR-009)."""
        seen: dict[str, None] = {}
        for rec in self._records:
            for term in rec.missing_focus:
                seen.setdefault(term, None)
        return list(seen)

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self._records]

    def __len__(self) -> int:
        return len(self._records)
