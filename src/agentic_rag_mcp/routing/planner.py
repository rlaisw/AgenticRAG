"""Planner: decompose complex questions into routed sub-tasks (FR-013)."""

from __future__ import annotations

TOOLS = ("vector_search", "sql_query", "web_search", "onedrive", "sharepoint", "graphify")


def decompose(question: str, available_tools: list[str] | None = None) -> list[dict]:
    """Deterministic heuristic planner for v1; an LLM-backed planner can replace
    this behind the same interface."""
    available = set(available_tools or ("vector_search",))
    tasks = []
    q = question.lower()

    def add(tool: str, sub_query: str) -> None:
        if tool in available:
            tasks.append({"id": f"t{len(tasks)+1}", "tool": tool, "input": sub_query.strip()})

    if " and " in q or " vs " in q or "compare" in q:
        parts = q.replace(" vs ", " and ").split(" and ")
        for part in parts:
            if len(part.strip()) > 3:
                add("vector_search", part)
                add("web_search", part)
    else:
        add("vector_search", question)
        if any(w in q for w in ("table", "rows", "sqlite", "database", "numbers")):
            add("sql_query", question)
        if any(w in q for w in ("latest", "recent", "news", "2025", "2026", "today")):
            add("web_search", question)
    if not tasks:
        tasks = [{"id": "t1", "tool": next(iter(available), "vector_search"), "input": question}]
    return tasks
