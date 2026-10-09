"""Integration: web_research end to end over the local fixture server with the
engine chain mocked (research.md D6 rows 3, 4, 11; SC-004; FR-008/014)."""

import asyncio
import json

import pytest

from agentic_rag_mcp.config import Config
from agentic_rag_mcp.server import build_server

FIX = {"normal": "/normal", "slow": "/slow", "forbidden": "/forbidden"}


def call(server, name, args):
    raw = asyncio.run(server.call_tool(name, args))
    structured = [b["result"] for b in raw if isinstance(b, dict) and "result" in b]
    if structured:
        return structured[0]
    texts = [getattr(b, "text", "") for b in raw if getattr(b, "text", "")]
    joined = "".join(texts).strip()
    return json.loads(joined) if joined else None


class FakeProvider:
    name = "searxng"

    def __init__(self, urls):
        self._hits = [{"title": f"page {i}", "url": u, "snippet": f"snippet {i}"}
                      for i, u in enumerate(urls)]

    def search(self, query, limit=5):
        return self._hits[:limit]


def _server(tmp_path, monkeypatch, urls, fetch_timeout_s=1.0, **cfg_over):
    import agentic_rag_mcp.server as server_mod
    import agentic_rag_mcp.search.web.research as research_mod

    monkeypatch.setattr(server_mod, "build_providers",
                        lambda cfg: [FakeProvider(urls)])
    # The fixture server runs on 127.0.0.1, which the SSRF guard (correctly)
    # refuses. The guard is unit-tested separately (test_research_guard.py);
    # here we bypass the trust boundary for the fixture host only.
    monkeypatch.setattr(research_mod, "_assert_public_host", lambda host: None)
    cfg = Config(state_db=tmp_path / "s.sqlite3", vector_dir=tmp_path / "v",
                 decider_enabled=False, research_fetch_timeout_s=fetch_timeout_s, **cfg_over)
    return build_server(cfg)


def _hits_by_url(out):
    return {h["url"]: h for h in out["hits"]}


def test_normal_page_scraped_with_grouped_content(tmp_path, monkeypatch, fixture_web_server):
    srv = _server(tmp_path, monkeypatch, [f"{fixture_web_server}/normal"])
    out = call(srv, "web_research", {"query": "trace"})
    h = out["hits"][0]
    assert h["scrape"]["status"] == "ok"
    assert h["scrape"]["sections"][0]["blocks"][0]["type"] == "p"
    assert "Exchange admin center" in h["content"]               # grouped, bounded
    assert h["content"] and h["engine"] == "searxng"


def test_slow_page_falls_back_to_snippet_marked_timeout(tmp_path, monkeypatch, fixture_web_server):
    srv = _server(tmp_path, monkeypatch, [f"{fixture_web_server}/slow"])
    out = call(srv, "web_research", {"query": "trace"})
    h = out["hits"][0]
    assert h["scrape"]["status"] == "fallback"                    # D6 row 3
    assert h["scrape"]["status_reason"] == "timeout"
    assert h["content"] == h["snippet"]                            # honest fallback (FR-008)


def test_forbidden_page_falls_back_marked_http_403(tmp_path, monkeypatch, fixture_web_server):
    srv = _server(tmp_path, monkeypatch, [f"{fixture_web_server}/forbidden"])
    out = call(srv, "web_research", {"query": "trace"})
    h = out["hits"][0]
    assert h["scrape"]["status"] == "fallback"                     # D6 row 4
    assert h["scrape"]["status_reason"] == "http:403"
    assert h["content"]                                            # SC-004: never empty


def test_every_hit_yields_content_mixed_paths(tmp_path, monkeypatch, fixture_web_server):
    urls = [f"{fixture_web_server}/normal", f"{fixture_web_server}/slow",
            f"{fixture_web_server}/forbidden"]
    srv = _server(tmp_path, monkeypatch, urls)
    out = call(srv, "web_research", {"query": "trace", "limit": 3})
    by_url = _hits_by_url(out)
    assert len(by_url) == 3
    assert all(h["content"] for h in by_url.values())              # SC-004 across all paths
    statuses = sorted(h["scrape"]["status"] for h in by_url.values())
    assert statuses == ["fallback", "fallback", "ok"]


def test_ask_live_web_evidence_uses_grouped_content(tmp_path, monkeypatch, fixture_web_server):
    """FR-012: the reflexion loop's web evidence carries grouped page content —
    the fixture page's actual text appears in the answer, not just a snippet."""
    srv = _server(tmp_path, monkeypatch, [f"{fixture_web_server}/normal"])
    out = call(srv, "ask", {"question": "latest news on tracing an email message", "mode": "deep"})
    assert "Exchange admin center" in out["answer"]           # grouped fixture content (FR-012)


def test_overall_bound_cuts_off_with_honest_fallback(tmp_path, monkeypatch, fixture_web_server):
    """D6 row 11 / FR-014: slow pages past the reduced overall bound end as
    fallback with cut-off reason; the call itself returns promptly."""
    import time as _time

    srv = _server(tmp_path, monkeypatch, [f"{fixture_web_server}/slow"] * 2,
                  fetch_timeout_s=8.0, research_overall_timeout_s=2.0)
    t0 = _time.perf_counter()
    out = call(srv, "web_research", {"query": "trace", "limit": 2})
    elapsed = _time.perf_counter() - t0
    assert elapsed < 10.0                                          # never hangs past the bound
    reasons = {h["scrape"]["status_reason"] for h in out["hits"]}
    assert any("cut-off-at-overall-bound" in r for r in reasons)  # honest cut-off
    assert all(h["content"] for h in out["hits"])                 # snippets serve the content
