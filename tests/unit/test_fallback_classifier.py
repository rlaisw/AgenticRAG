from agentic_rag_mcp.routing.fallback import heuristic_classify


def test_simple_question_fast():
    assert heuristic_classify("What is the capital of France?") == "fast"


def test_multi_part_question_deliberative():
    assert heuristic_classify(
        "Compare Apollo and Gemini results and explain why revenue grew") == "deliberative"


def test_default_is_deliberative():
    assert heuristic_classify("Document something ambiguous") == "deliberative"
