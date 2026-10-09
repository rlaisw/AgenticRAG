"""SSRF guard (FR-013; research.md D6 row 6): private/loopback/link-local
destinations refused — including via redirects. Resolver is exercised with IP
literals and localhost (no network); the public/redirect cases mock httpx."""

import httpx
import pytest

from agentic_rag_mcp.search.web.research import ScrapeBlocked, guarded_get


class _Resp:
    def __init__(self, status=200, location=None):
        self.status_code = status
        self.headers = {"location": location} if location else {}
        self.text = "<html><body>ok</body></html>"

    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/x",            # loopback
    "http://localhost/x",            # loopback name
    "http://10.0.0.1/x",             # private
    "http://192.168.1.1/x",          # private
    "http://169.254.169.254/x",      # link-local (cloud metadata)
    "http://[::1]/x",                # loopback v6
])
def test_private_destinations_refused(url):
    with pytest.raises(ScrapeBlocked) as exc:
        guarded_get(url, timeout=1.0)
    assert "blocked-private-address" in exc.value.reason


def test_public_ip_allowed_and_returned(monkeypatch):
    calls = []

    def fake_get(url, timeout, follow_redirects, headers):
        calls.append(url)
        return _Resp(200)

    monkeypatch.setattr(httpx, "get", fake_get)
    resp = guarded_get("http://93.184.216.34/x", timeout=1.0)
    assert resp.status_code == 200 and calls == ["http://93.184.216.34/x"]


def test_redirect_to_private_refused(monkeypatch):
    def fake_get(url, timeout, follow_redirects, headers):
        return _Resp(302, location="http://10.0.0.99/steal")

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(ScrapeBlocked) as exc:
        guarded_get("http://93.184.216.34/x", timeout=1.0)
    assert "blocked-private-address" in exc.value.reason  # hop-by-hop check (D4)


def test_redirect_chain_capped(monkeypatch):
    def fake_get(url, timeout, follow_redirects, headers):
        return _Resp(302, location=url)  # infinite self-redirect

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(ScrapeBlocked) as exc:
        guarded_get("http://93.184.216.34/x", timeout=1.0)
    assert "too-many-redirects" in exc.value.reason
