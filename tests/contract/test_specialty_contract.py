"""Contract: specialty_search + specialty_profiles response schemas (FR-005/009, SC-004)."""

import asyncio
import json

import pytest

from agentic_rag_mcp.config import Config
from agentic_rag_mcp.server import build_server


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

    def __init__(self, hits):
        self._hits = hits
        self.queries = []

    def search(self, query, limit=5):
        self.queries.append(query)  # record for scoping verification
        return self._hits[:limit]


HITS = [
    {"title": "DKIM Guide", "url": "https://learn.microsoft.com/exchange/dkim",
     "snippet": "Configure DKIM..."},
    {"title": "Random Blog", "url": "https://randomblog.com/dkim",
     "snippet": "Should be filtered out."},
    {"title": "Community", "url": "https://techcommunity.microsoft.com/t/dkim",
     "snippet": "DKIM discussion"},
]


@pytest.fixture
def server(tmp_path, monkeypatch):
    import agentic_rag_mcp.server as server_mod

    provider = FakeProvider(HITS)  # single instance so we can inspect queries
    profiles = tmp_path / "specialty_profiles.json"
    profiles.write_text(json.dumps({
        "microsoft": {"sites": ["learn.microsoft.com", "techcommunity.microsoft.com"],
                       "description": "Microsoft docs"}}))
    monkeypatch.setattr(server_mod, "build_providers", lambda cfg: [provider])
    cfg = Config(state_db=tmp_path / "s.sqlite3", vector_dir=tmp_path / "v",
                 decider_enabled=False,
                 specialty_profiles_file=str(profiles))
    srv = build_server(cfg)
    srv._test_provider = provider  # expose for query inspection
    return srv


def test_specialty_search_returns_only_matching_domains(server):
    out = call(server, "specialty_search", {"query": "DKIM", "profile": "microsoft", "limit": 5})
    provider = server._test_provider
    assert provider.queries  # chain was called
    assert any("site:learn.microsoft.com" in q for q in provider.queries)  # scoping sent
    assert isinstance(out, list)
    assert len(out) == 2  # randomblog filtered out (FR-006)
    assert all("microsoft.com" in h["url"] for h in out)
    assert all(set(h) >= {"title", "url", "snippet", "engine"} for h in out)


def test_specialty_profiles_returns_full_json(server):
    out = call(server, "specialty_profiles", {})
    assert out == {"microsoft": {"sites": ["learn.microsoft.com", "techcommunity.microsoft.com"],
                                 "description": "Microsoft docs"}}


def test_specialty_search_invalid_profile_honest_error(server):
    out = call(server, "specialty_search", {"query": "x", "profile": "nonexistent"})
    assert out["error"] and "nonexistent" in out["error"]          # FR-007
    assert "microsoft" in out["available"]                         # lists available


def test_existing_web_search_canary_unchanged(server):
    """SC-004: web_search frozen — the existing tool still works through the same server."""
    out = call(server, "web_search", {"query": "DKIM"})
    assert isinstance(out, list) and len(out) == 3  # all hits, no domain filter on web_search
