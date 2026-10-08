"""Rule-based Evaluator (FR-007, FR-010, research.md D5): score + verdict, deterministic."""

from agentic_rag_mcp.agents.evaluator import evaluate


def _ev(document_id="d1"):
    return [{"snippet": "text", "document_id": document_id}]


def test_identical_inputs_identical_outputs():
    a = evaluate("When did the voyager launch?", "the voyager launch happened in 1977", _ev())
    b = evaluate("When did the voyager launch?", "the voyager launch happened in 1977", _ev())
    assert a == b


def test_full_coverage_with_citations_passes_with_high_score():
    score, verdict, missing = evaluate(
        "When did the voyager launch?", "voyager launch 1977 probe", _ev() + _ev())
    assert verdict == "pass"
    assert score >= 8
    assert missing == []


def test_partial_coverage_fails_and_names_missing_terms():
    score, verdict, missing = evaluate(
        "When did the voyager launch?", "a mission happened once", _ev())
    assert verdict == "fail"
    assert missing  # names what the draft misses
    assert score < 8


def test_no_citable_evidence_caps_score_and_fails():
    score, verdict, _ = evaluate(
        "When did the voyager launch?", "voyager launch 1977", [{"snippet": "x"}])
    assert verdict == "fail"
    assert score <= 5  # halved per D5


def test_score_always_in_1_10():
    score, _, _ = evaluate("What happened?", "nothing", [])
    assert 1 <= score <= 10


def test_hit_count_is_scoring_input_not_verdict_gate():
    """FR-010: hit counts feed the score; they do not gate the verdict."""
    from agentic_rag_mcp.agents.evaluator import MIN_HITS
    from agentic_rag_mcp.agents.sufficiency import MIN_HITS as SUFF_HITS

    assert MIN_HITS == SUFF_HITS
    one = evaluate("voyager launch year", "voyager launch year 1977", _ev()[:1])
    two = evaluate("voyager launch year", "voyager launch year 1977", _ev() + _ev())
    assert one[1] == "pass"          # input, not gate — a single good hit can pass
    assert one[0] < two[0]            # but fewer hits score lower
