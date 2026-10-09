"""Extended provider chain (FR-001/003/004; research.md D6 rows 1, 2, 10):
per-hit engine provenance, URL dedup keeping first ranking, engine-down
fallback, and honest all-engines-down error state."""

import pytest

from agentic_rag_mcp.errors import ProviderError
from agentic_rag_mcp.search.web.base import search_all


class FakeProvider:
    def __init__(self, name, hits=None, error=False):
        self.name = name
        self._hits = hits or []
        self._error = error

    def search(self, query: str, limit: int = 5):
        if self._error:
            raise ProviderError(f"{self.name} failed")
        return self._hits[:limit]


def _hit(url, title="t"):
    return {"title": title, "url": url, "snippet": "s"}


def test_per_hit_engine_provenance_and_frozen_fields():
    providers = [FakeProvider("searxng", [_hit("https://a.example/1")])]
    hits, engines_used, error = search_all(providers, "q")
    assert hits[0] == {"title": "t", "url": "https://a.example/1", "snippet": "s",
                       "engine": "searxng"}
    assert engines_used == ["searxng"]
    assert error is None


def test_engine_down_next_engine_serves():
    providers = [FakeProvider("searxng", error=True),
                 FakeProvider("tavily", [_hit("https://b.example/1")])]
    hits, engines_used, error = search_all(providers, "q")
    assert hits and hits[0]["engine"] == "tavily"      # FR-003
    assert engines_used == ["tavily"]
    assert error is None


def test_duplicate_urls_across_engines_dedup_keeps_first_ranking():
    shared = _hit("https://shared.example/1", title="from-searxng")
    providers = [FakeProvider("searxng", [shared]),
                 FakeProvider("tavily", [_hit("https://shared.example/1", title="from-tavily"),
                                         _hit("https://only-tavily.example/2")])]
    hits, _, _ = search_all(providers, "q")
    urls = [h["url"] for h in hits]
    assert urls.count("https://shared.example/1") == 1        # FR-004
    assert hits[0]["title"] == "from-searxng"                  # first ranking kept
    assert "https://only-tavily.example/2" in urls


def test_all_engines_down_honest_empty_with_error():
    providers = [FakeProvider("searxng", error=True), FakeProvider("tavily", error=True)]
    hits, engines_used, error = search_all(providers, "q")
    assert hits == [] and engines_used == []
    assert error is not None and "failed" in error["message"].lower()  # US1-AC4, never fabricated


def test_no_providers_configured_is_error_state():
    hits, engines_used, error = search_all([], "q")
    assert hits == [] and error is not None


def test_healthy_engine_zero_hits_is_honest_empty_not_error():
    providers = [FakeProvider("searxng", [])]
    hits, engines_used, error = search_all(providers, "q")
    assert hits == [] and error is None
