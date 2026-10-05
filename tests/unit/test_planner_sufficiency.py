from agentic_rag_mcp.agents.sufficiency import assess
from agentic_rag_mcp.routing.planner import decompose


def test_sufficiency_satisfied():
    hits = [{"snippet": "a"}, {"snippet": "b"}]
    assert assess("q", hits, 0, 5)["outcome"] == "satisfied"


def test_sufficiency_exhausted_at_budget():
    assert assess("q", [], 4, 5)["outcome"] == "exhausted"


def test_sufficiency_continue():
    assert assess("q", [{"snippet": "a"}], 0, 5)["outcome"] == "continue"


def test_planner_multi_part():
    tasks = decompose("Compare Apollo landings and revenue growth",
                      ["vector_search", "web_search"])
    tools = {t["tool"] for t in tasks}
    assert "vector_search" in tools and "web_search" in tools
    assert len(tasks) >= 2


def test_planner_sql_keyword_routes_sql(tmp_path):
    tasks = decompose("Show numbers from the database table",
                      ["vector_search", "sql_query"])
    assert any(t["tool"] == "sql_query" for t in tasks)


def test_planner_default_vector():
    tasks = decompose("What is the moon landing?", ["vector_search"])
    assert tasks == [{"id": "t1", "tool": "vector_search", "input": "What is the moon landing?"}]
