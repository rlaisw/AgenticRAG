"""OneDrive source (FR-005..FR-014; research.md D7 error matrix):
pagination, delta parsing, download, size cap, format filtering, auth errors."""

import httpx
import pytest

from agentic_rag_mcp.errors import ProviderError, SourceAuthError
from agentic_rag_mcp.sources.onedrive import OneDriveSource


class FakeAuth:
    def token(self):
        return "fake-token"


def _item(item_id, name, size=1000, download_url="https://dl.example/file", **extra):
    d = {"id": item_id, "name": name, "size": size,
         "@microsoft.graph.downloadUrl": download_url, "file": {"mimeType": "application/pdf"}}
    d.update(extra)
    return d


def _mock_graph(monkeypatch, responses):
    """Mock httpx.get to return Graph API responses in order (with nextLink pages)."""
    calls = []

    def fake_get(url, headers=None, params=None, timeout=None, follow_redirects=None):
        calls.append({"url": url, "params": params})
        # find matching response by URL substring
        for pattern, resp_data in responses:
            if pattern in url:
                return httpx.Response(200, json=resp_data, request=httpx.Request("GET", url))
        # default: empty page with deltaLink
        return httpx.Response(200, json={"value": [], "@odata.deltaLink": "https://g/delta/next"},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def _src(config=None):
    return OneDriveSource(FakeAuth(), config or {})


def test_pagination_follows_next_link(monkeypatch):
    """FR-014: @odata.nextLink followed across multiple pages."""
    _mock_graph(monkeypatch, [
        ("delta", {"value": [_item(f"i{i}", f"f{i}.pdf") for i in range(3)],
                    "@odata.nextLink": "https://g/page2"}),
        ("page2", {"value": [_item("i3", "f3.pdf")],
                    "@odata.deltaLink": "https://g/delta/next"}),
    ])
    result = _src().delta()
    assert len(result["items"]) == 4  # all pages followed
    assert result["delta_link"] == "https://g/delta/next"


def test_initial_delta_returns_all_as_added(monkeypatch):
    """First sync (no cursor): all items classified as added."""
    _mock_graph(monkeypatch, [
        ("delta", {"value": [_item("a", "doc.pdf"), _item("b", "sheet.xlsx")],
                    "@odata.deltaLink": "https://g/delta/c1"}),
    ])
    result = _src().sync({})
    assert len(result["added"]) == 2
    assert len(result["updated"]) == 0
    assert result["delta_link"] == "https://g/delta/c1"


def test_subsequent_delta_returns_changes(monkeypatch):
    """With cursor: adds + modifies + deletes classified correctly."""
    _mock_graph(monkeypatch, [
        ("delta/c1", {"value": [
            _item("new", "new.pdf"),
            _item("mod", "mod.pdf"),
            {"id": "gone", "name": "old.pdf", "deleted": {"state": "deleted"}},
        ], "@odata.deltaLink": "https://g/delta/c2"}),
    ])
    result = _src({"delta_link": "https://g/delta/c1"}).sync({"delta_link": "https://g/delta/c1"})
    assert len(result["added"]) == 0  # with cursor, new files are "updated" (changed)
    assert len(result["updated"]) == 2
    assert len(result["deleted"]) == 1
    assert result["deleted"][0]["locator"] == "gone"
    assert result["delta_link"] == "https://g/delta/c2"


def test_unsupported_format_skipped_with_reason(monkeypatch):
    """FR-007: images/executables skipped with honest reason."""
    _mock_graph(monkeypatch, [
        ("delta", {"value": [_item("p", "photo.png"), _item("d", "doc.pdf")],
                    "@odata.deltaLink": "https://g/d"}),
    ])
    result = _src().sync({})
    assert len(result["added"]) == 1  # only the pdf
    assert len(result["skipped"]) == 1
    assert "unsupported" in result["skipped"][0]["reason"]


def test_oversized_file_skipped_with_reason(monkeypatch):
    """FR-008: >50 MB files skipped."""
    _mock_graph(monkeypatch, [
        ("delta", {"value": [_item("big", "huge.pdf", size=60 * 1024 * 1024)],
                    "@odata.deltaLink": "https://g/d"}),
    ])
    result = _src().sync({})
    assert len(result["added"]) == 0
    assert "too large" in result["skipped"][0]["reason"]


def test_empty_drive_healthy_zero_files(monkeypatch):
    """Edge: empty OneDrive → 0 files, no error."""
    _mock_graph(monkeypatch, [
        ("delta", {"value": [], "@odata.deltaLink": "https://g/d"}),
    ])
    result = _src().sync({})
    assert result["added"] == [] and result["skipped"] == []


def test_auth_error_raises_source_auth_error(monkeypatch):
    """401 from Graph → SourceAuthError (marks source degraded)."""
    def fake_get(url, **kw):
        return httpx.Response(401, json={}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(SourceAuthError):
        _src().delta()


def test_rate_limit_raises_provider_error(monkeypatch):
    """429 → ProviderError (retry next cycle)."""
    def fake_get(url, **kw):
        return httpx.Response(429, json={}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(ProviderError, match="rate limited"):
        _src().delta()


def test_folder_path_used_in_delta_url(monkeypatch):
    """Configured folder_path reflected in the delta URL."""
    calls = _mock_graph(monkeypatch, [("delta", {"value": [], "@odata.deltaLink": "https://g/d"})])
    _src({"folder_path": "/Documents"}).delta()
    assert any("root:/Documents:/delta" in c["url"] for c in calls)


def test_download_returns_bytes(monkeypatch):
    """D4: download via pre-authenticated URL returns file content."""
    def fake_get(url, timeout=None, follow_redirects=None):
        return httpx.Response(200, content=b"pdf-bytes", request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", fake_get)
    assert OneDriveSource.download("https://dl.example/file") == b"pdf-bytes"
