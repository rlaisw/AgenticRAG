"""Contract tests for web providers: normalized shape, failure -> ProviderError."""

import pytest
import respx
import httpx

from agentic_rag_mcp.errors import ProviderError
from agentic_rag_mcp.search.web.base import TavilyProvider, ExaProvider, SearxngProvider


@respx.mock
def test_tavily_normalizes_results():
    respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(200, json={"results": [
            {"title": "t", "url": "https://x", "content": "c"}]}))
    hits = TavilyProvider("k").search("q", limit=1)
    assert hits == [{"title": "t", "url": "https://x", "snippet": "c"}]


@respx.mock
def test_exa_timeout_raises_provider_error():
    respx.post("https://api.exa.ai/search").mock(side_effect=httpx.ConnectTimeout("boom"))
    with pytest.raises(ProviderError) as ei:
        ExaProvider("k").search("q")
    assert ei.value.code.value == "ProviderUnavailable"


@respx.mock
def test_searxng_respects_limit():
    respx.get("http://searx/search").mock(
        return_value=httpx.Response(200, json={"results": [
            {"title": f"t{i}", "url": f"https://x/{i}", "content": "c"} for i in range(10)]}))
    hits = SearxngProvider("http://searx").search("q", limit=3)
    assert len(hits) == 3 and hits[0]["url"] == "https://x/0"


def test_unconfigured_provider_raises():
    with pytest.raises(ProviderError):
        TavilyProvider("")
