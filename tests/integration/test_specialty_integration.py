"""Integration: specialty_search end-to-end through the real server (SC-001/002/003;
research.md D2 hot-reload, D4 substring matching, D6 honest empties)."""

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

    def search(self, query, limit=5):
        return self._hits[:limit]


MIXED_HITS = [
    {"title": "MS Learn", "url": "https://learn.microsoft.com/exchange", "snippet": "official docs"},
    {"title": "Huawei Support", "url": "https://support.huawei.com/switch", "snippet": "huawei docs"},
    {"title": "Blog", "url": "https://randomblog.com/exchange", "snippet": "unofficial"},
    {"title": "MS Community", "url": "https://techcommunity.microsoft.com/t/123", "snippet": "community"},
]


def _server(tmp_path, monkeypatch, profiles_content=None):
    import agentic_rag_mcp.server as server_mod

    profiles = tmp_path / "specialty_profiles.json"
    if profiles_content:
        profiles.write_text(json.dumps(profiles_content))
    monkeypatch.setattr(server_mod, "build_providers", lambda cfg: [FakeProvider(MIXED_HITS)])
    cfg = Config(state_db=tmp_path / "s.sqlite3", vector_dir=tmp_path / "v",
                 decider_enabled=False, specialty_profiles_file=str(profiles))
    return build_server(cfg)


def test_results_filtered_to_matching_domains(tmp_path, monkeypatch):
    """SC-001: 100% of results contain a configured domain (substring match)."""
    srv = _server(tmp_path, monkeypatch, {
        "microsoft": {"sites": ["microsoft.com"], "description": "MS docs"}})
    out = call(srv, "specialty_search", {"query": "exchange", "profile": "microsoft"})
    assert all("microsoft.com" in h["url"] for h in out)
    assert len(out) == 2  # learn.microsoft.com + techcommunity.microsoft.com (huawei/randomblog filtered)


def test_hot_reload_new_profile_immediately_usable(tmp_path, monkeypatch):
    """SC-002: add a profile to the JSON file → usable on the NEXT call, no restart."""
    profiles = tmp_path / "specialty_profiles.json"
    profiles.write_text(json.dumps({
        "microsoft": {"sites": ["microsoft.com"], "description": "MS"}}))
    srv = _server(tmp_path, monkeypatch)  # server built with just microsoft
    # add huawei profile while the server is running
    d = json.loads(profiles.read_text())
    d["huawei"] = {"sites": ["huawei.com"], "description": "Huawei"}
    profiles.write_text(json.dumps(d))
    # immediately search with the new profile — no restart
    out = call(srv, "specialty_search", {"query": "switch", "profile": "huawei"})
    assert all("huawei.com" in h["url"] for h in out)
    assert len(out) == 1  # only support.huawei.com


def test_zero_scoped_results_honest_empty(tmp_path, monkeypatch):
    """Constitution IV / Clarifications: no auto-fallback; honest empty list."""
    profiles = tmp_path / "specialty_profiles.json"
    profiles.write_text(json.dumps({
        "nosuch": {"sites": ["thisdomaindoesnotexistanywhere.com"],
                    "description": "no results"}}))
    srv = _server(tmp_path, monkeypatch)
    out = call(srv, "specialty_search", {"query": "test", "profile": "nosuch"})
    assert out == []  # honest empty — NOT general results, NOT an error


def test_case_insensitive_profile_lookup(tmp_path, monkeypatch):
    """FR-003: 'Microsoft' = 'microsoft'."""
    srv = _server(tmp_path, monkeypatch, {
        "microsoft": {"sites": ["microsoft.com"], "description": "MS"}})
    out = call(srv, "specialty_search", {"query": "x", "profile": "Microsoft"})
    assert isinstance(out, list)  # no error — profile resolved case-insensitively


def test_missing_profiles_file_honest_error(tmp_path, monkeypatch):
    """FR-004: no file → explicit error, never a crash."""
    srv = _server(tmp_path, monkeypatch)  # no profiles file written
    out = call(srv, "specialty_search", {"query": "x", "profile": "any"})
    assert isinstance(out, dict) and out["error"]  # honest error
    out2 = call(srv, "specialty_profiles", {})
    assert isinstance(out2, dict) and out2["error"]
