"""Tests for the Graphify wrapper: disabled default, missing graph, CLI shell-out."""

import json
from unittest.mock import patch

import pytest

from agentic_rag_mcp.errors import FeatureDisabledError, NotFoundError, ProviderError
from agentic_rag_mcp.search.graphify_search import GraphifySearch


def test_disabled_by_default(tmp_path):
    g = GraphifySearch(tmp_path / "graph.json", enabled=False)
    with pytest.raises(FeatureDisabledError) as ei:
        g.explain("x")
    assert ei.value.code.value == "FeatureDisabled"


def test_enabled_but_graph_missing(tmp_path):
    g = GraphifySearch(tmp_path / "graph.json", enabled=True)
    with pytest.raises(NotFoundError):
        g.explain("x")


def test_stats_reads_graph(tmp_path):
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"nodes": [{"id": 1}, {"id": 2}], "edges": [{"a": 1, "b": 2}]}))
    g = GraphifySearch(graph, enabled=True)
    assert g.stats() == {"nodes": 2, "edges": 1, "graph": str(graph)}


def test_explain_shells_out(tmp_path):
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"nodes": [], "edges": []}))
    g = GraphifySearch(graph, enabled=True)
    with patch("agentic_rag_mcp.search.graphify_search.subprocess.run") as run:
        run.return_value = type("P", (), {"returncode": 0, "stdout": "answer text",
                                          "stderr": ""})()
        out = g.explain("Foo")
    assert out["answer"] == "answer text"
    assert run.call_args.args[0][:2] == ["graphify", "explain"]


def test_cli_failure_is_provider_error(tmp_path):
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"nodes": [], "edges": []}))
    g = GraphifySearch(graph, enabled=True)
    with patch("agentic_rag_mcp.search.graphify_search.subprocess.run") as run:
        run.return_value = type("P", (), {"returncode": 2, "stdout": "",
                                          "stderr": "graph file corrupt"})()
        with pytest.raises(ProviderError):
            g.explain("Foo")
