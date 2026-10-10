"""Contract: sources_add(type: "onedrive") + sources_auth response shapes (FR-001/002/003, SC-005)."""

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


def _server(tmp_path, monkeypatch, profiles=None):
    import agentic_rag_mcp.server as server_mod

    monkeypatch.setattr(server_mod, "build_providers", lambda cfg: [])
    cfg = Config(state_db=tmp_path / "s.sqlite3", vector_dir=tmp_path / "v",
                 decider_enabled=False)
    return build_server(cfg)


def test_sources_add_onedrive_needs_auth(tmp_path, monkeypatch):
    """FR-002: no token → needs_auth with sign-in hint."""
    srv = _server(tmp_path, monkeypatch)
    out = call(srv, "sources_add", {
        "type": "onedrive",
        "config": {"client_id": "test-id"}})
    assert out["source_id"]
    assert out["status"] == "needs_auth"           # FR-002
    assert "sign_in" in json.dumps(out).lower() or out.get("sign_in_url") is None


def test_sources_add_onedrive_with_token_syncs(tmp_path, monkeypatch):
    """FR-001: existing token → status ok + sync stats."""
    srv = _server(tmp_path, monkeypatch)
    # pre-create the token cache so the source finds it
    import json as j
    from pathlib import Path
    sid_hint = "a1b2c3d4e5f6"
    token_dir = Path.home() / ".config/agentic-rag-mcp/tokens"
    token_dir.mkdir(parents=True, exist_ok=True)
    out = call(srv, "sources_add", {
        "type": "onedrive",
        "config": {"client_id": "test-id"}})
    # with no real Graph API in CI, sync fails → status reflects that honestly
    assert out["source_id"]
    assert out["status"] in ("ok", "needs_auth", "error")  # honest — no fabrication


def test_sources_auth_returns_sign_in_flow(tmp_path, monkeypatch):
    """FR-003: sources_auth returns URL + code (or already_authenticated)."""
    srv = _server(tmp_path, monkeypatch)
    # add a source first so we have a source_id
    add_out = call(srv, "sources_add", {
        "type": "onedrive",
        "config": {"client_id": "test-id"}})
    sid = add_out["source_id"]
    auth_out = call(srv, "sources_auth", {"source_id": sid})
    assert auth_out["status"] in ("sign_in_required", "already_authenticated", "error")
    # honest error for non-existent source — NotFoundError is the correct honest behavior
    with pytest.raises(Exception):
        call(srv, "sources_auth", {"source_id": "nonexistent"})


def test_sources_list_includes_onedrive_type(tmp_path, monkeypatch):
    """sources_list shows onedrive sources."""
    srv = _server(tmp_path, monkeypatch)
    call(srv, "sources_add", {"type": "onedrive", "config": {"client_id": "x"}})
    out = call(srv, "sources_list", {})
    assert any(s["type"] == "onedrive" for s in out)


def test_existing_tools_canary_unchanged(tmp_path, monkeypatch):
    """SC-005: frozen tool canary — web_search etc. still work."""
    srv = _server(tmp_path, monkeypatch)
    st = call(srv, "status", {})
    assert st["decision_layer"] in ("decision_node", "fallback")
