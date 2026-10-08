"""EpisodicMemory + ReflectionRecord semantics (FR-009, FR-012)."""

from agentic_rag_mcp.agents.memory import EpisodicMemory, ReflectionRecord


def _rec(iteration, missing, verdict="fail", score=4):
    return ReflectionRecord(iteration=iteration, evaluator_score=score,
                           evaluator_verdict=verdict, critique=f"critique {iteration}",
                           missing_focus=missing)


def test_memory_starts_empty_per_request():
    assert len(EpisodicMemory()) == 0
    assert EpisodicMemory().to_list() == []


def test_append_ordering_preserved():
    m = EpisodicMemory()
    m.append(_rec(1, ["apollo"]))
    m.append(_rec(2, ["revenue"]))
    assert [r["iteration"] for r in m.to_list()] == [1, 2]


def test_union_missing_focus_is_full_history_not_latest():
    """FR-009: every subsequent trial is conditioned on the FULL history."""
    m = EpisodicMemory()
    m.append(_rec(1, ["apollo", "landing"]))
    m.append(_rec(2, ["revenue"]))
    assert m.union_missing_focus() == ["apollo", "landing", "revenue"]


def test_union_deduplicates_terms_in_first_appearance_order():
    m = EpisodicMemory()
    m.append(_rec(1, ["apollo"]))
    m.append(_rec(2, ["revenue", "apollo"]))
    assert m.union_missing_focus() == ["apollo", "revenue"]


def test_no_cross_request_leakage():
    """FR-012: memory is per-request; a fresh instance never sees old records."""
    m1 = EpisodicMemory()
    m1.append(_rec(1, ["x"]))
    assert len(EpisodicMemory()) == 0


def test_record_serializes_all_fields():
    r = _rec(3, ["q"], verdict="pass", score=9).to_dict()
    assert r == {"iteration": 3, "evaluator_score": 9, "evaluator_verdict": "pass",
                 "critique": "critique 3", "missing_focus": ["q"]}
