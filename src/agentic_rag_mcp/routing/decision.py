"""System 1 decision node: embedded Laya decider — one pass, three primitives
(choice / score / noul), schema-validated, timeout-guarded (FR-001..FR-004).

Invalid/failed decider outcomes return DecisionResult(valid=False); the caller
falls back to the keyword heuristic with provenance "fallback" (FR-003).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..config import Config

ROUTE_OPTIONS = ("direct_retrieval", "deliberative_reasoning", "live_web", "source_management")

_ROUTE_CRITERIA = {
    "direct_retrieval": "any factual question that a document collection may plausibly answer — business results, reports, notes, reference material, or domain facts that could exist in the local knowledge base",
    "deliberative_reasoning": "a multi-part, comparative, or analytical question needing several retrieval steps and self-checking",
    "live_web": "only questions about the current time, date, live weather, breaking news, or real-time data that no stored document collection can ever contain",
    "source_management": "adding, listing, syncing, or removing the document sources of the knowledge base",
}

_COMPLEXITY_RUBRIC = [
    "trivial single-fact lookup",
    "simple factual question",
    "simple question with a qualifier",
    "moderate question needing one focused retrieval",
    "moderate question with two facets",
    "moderately complex multi-facet question",
    "complex question needing several retrievals",
    "complex comparative or multi-part question",
    "very complex analytical question",
    "research-grade multi-part question",
]

_SUFFICIENCY_STATEMENT = "The local knowledge base alone is likely sufficient to answer this request."


@dataclass
class DecisionResult:
    """data-model.md DecisionResult."""

    route: str | None
    complexity: int | None
    sufficient: bool | None
    route_probabilities: dict = field(default_factory=dict)
    provenance: str = "decision_node"  # "decision_node" | "fallback"
    latency_ms: int = 0
    valid: bool = True

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "complexity": self.complexity,
            "sufficient": self.sufficient,
            "route_probabilities": self.route_probabilities,
            "provenance": self.provenance,
            "latency_ms": self.latency_ms,
            "valid": self.valid,
        }


def validate_output(result: DecisionResult) -> DecisionResult:
    """FR-002/FR-004: route in set, complexity an integer 1-10; failures invalidate."""
    if result.route not in ROUTE_OPTIONS:
        result.valid = False
    if not isinstance(result.complexity, int) or not 1 <= result.complexity <= 10:
        result.valid = False
    if result.provenance not in ("decision_node", "fallback"):
        result.valid = False
    return result


def map_model_output(output: dict, threshold: float) -> DecisionResult:
    """Map one system_one result to DecisionResult (research.md D4).

    Raises on any malformed shape; the caller treats exceptions as invalid.

    `sufficient` is DERIVED from the route choice (T031 calibration): the noul
    head on this checkpoint consistently answers "not sufficient" for any
    positive phrasing of an unverifiable claim (measured across three
    statement variants), while the route channel is well-calibrated —
    direct_retrieval IS the sufficiency judgment. The noul question stays in
    the schema for three-primitive fidelity (FR-001); its raw value is unused.
    """
    answers = output["answers"]
    route_ans = answers["route"]
    score_ans = answers["complexity"]
    route = route_ans["choice"]
    complexity = int(round(float(score_ans["score"])))
    complexity = max(1, min(10, complexity))
    return DecisionResult(
        route=route,
        complexity=complexity,
        sufficient=(route == "direct_retrieval"),
        route_probabilities=route_ans.get("probabilities", {}),
    )


def _questions() -> dict:
    return {
        "route": {"type": "choice", "instructions": "Which route should handle this request?",
                  "criteria": _ROUTE_CRITERIA},
        "complexity": {"type": "score", "instructions": "How complex is this request?",
                       "criteria": _COMPLEXITY_RUBRIC},
        "sufficient": {"type": "noul", "instructions": _SUFFICIENCY_STATEMENT},
    }


def decide(question: str, cfg: Config) -> DecisionResult:
    """One forward pass over the entire input (FR-001). Any failure => invalid."""
    started = time.perf_counter()
    try:
        from . import laya_runtime

        output = laya_runtime.system_one(cfg, question, _questions())
        result = map_model_output(output, cfg.decider_noul_threshold)
    except Exception:  # noqa: BLE001 — load failure, timeout, malformed: all => fallback
        result = DecisionResult(route=None, complexity=None, sufficient=None, valid=False)
    result.latency_ms = int((time.perf_counter() - started) * 1000)
    return validate_output(result)


def fallback_route(question: str) -> DecisionResult:
    """Keyword-heuristic fallback (FR-003): fast => direct, deep => deliberative."""
    from .fallback import heuristic_classify

    label = heuristic_classify(question)
    route = "direct_retrieval" if label == "fast" else "deliberative_reasoning"
    # ponytail: heuristic cannot score complexity; banded defaults (2/8) per data-model
    return DecisionResult(route=route, complexity=2 if label == "fast" else 8,
                         sufficient=None, provenance="fallback", valid=True)


def _test_cfg() -> Config:
    """Config for unit tests (no model load needed)."""
    return Config()
