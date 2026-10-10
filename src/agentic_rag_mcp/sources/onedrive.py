"""OneDrive source: Graph API connector with delta sync, pagination, download (FR-001..FR-014).

Delta queries are used for BOTH initial and incremental sync (research.md D1/D2):
the first delta call (no cursor) enumerates ALL files; subsequent calls (with
the persisted delta-link cursor) return only changes (adds/modifies/deletes).
Pagination via @odata.nextLink is always followed (FR-014).
"""

from __future__ import annotations

import httpx

from ..errors import ProviderError, SourceAuthError

GRAPH = "https://graph.microsoft.com/v1.0"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx"}


class GraphBase:
    type = "graph"

    def __init__(self, auth) -> None:
        self._auth = auth

    def _get(self, url: str, params: dict | None = None) -> dict:
        """GET with auth token, following @odata.nextLink pagination (FR-014)."""
        items: list[dict] = []
        next_url = f"{GRAPH}{url}"
        first = True
        while next_url:
            if first:
                resp = self._request(next_url, params)
                first = False
            else:
                resp = self._request(next_url, None)
            items.extend(resp.get("value", []))
            next_url = resp.get("@odata.nextLink")
        delta_link = resp.get("@odata.deltaLink")
        return {"items": items, "delta_link": delta_link}

    def _request(self, url: str, params: dict | None) -> dict:
        try:
            token = self._auth.token()
        except SourceAuthError:
            raise
        try:
            resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"},
                             params=params or {}, timeout=30.0)
            if resp.status_code in (401, 403):
                raise SourceAuthError(f"graph auth failed: {resp.status_code}")
            if resp.status_code == 429:
                raise ProviderError("graph rate limited (429) — retry next cycle")
            resp.raise_for_status()
            return resp.json()
        except SourceAuthError:
            raise
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"graph request failed: {exc}") from exc


class OneDriveSource(GraphBase):
    type = "onedrive"

    def __init__(self, auth, config: dict) -> None:
        super().__init__(auth)
        self._config = config

    def delta(self, delta_link: str | None = None) -> dict:
        """Delta query: returns {items, delta_link}. First call (no cursor) = full listing."""
        if delta_link:
            # subsequent sync — use the persisted cursor directly
            return self._get_url(delta_link)
        # initial sync — enumerate from the configured folder root
        folder = self._config.get("folder_path", "/") or "/"
        if folder == "/":
            url = "/me/drive/root/delta"
        else:
            url = f"/me/drive/root:{folder}:/delta"
        return self._get(url)

    def _get_url(self, url: str) -> dict:
        """GET a full URL (for delta cursors) with pagination."""
        items: list[dict] = []
        next_url = url
        resp = {}
        while next_url:
            resp = self._request(next_url, None)
            items.extend(resp.get("value", []))
            next_url = resp.get("@odata.nextLink")
        return {"items": items, "delta_link": resp.get("@odata.deltaLink")}

    @staticmethod
    def download(download_url: str, timeout: float = 60.0) -> bytes:
        """Download a file via its pre-authenticated Graph downloadUrl (D4)."""
        try:
            resp = httpx.get(download_url, timeout=timeout, follow_redirects=True)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"download failed: {exc}") from exc

    def sync(self, state: dict | None = None) -> dict:
        """Full sync cycle: delta → classify → return per-item results (research.md D6/D7).

        Returns {added, updated, deleted, skipped, delta_link} where added/updated
        items carry {locator, title, content} for the pipeline to parse+embed.
        The caller (pipeline) handles LanceDB eviction for deleted locators.
        """
        state = state or {}
        delta_link = state.get("delta_link")
        result = self.delta(delta_link)
        items, new_link = result["items"], result["delta_link"]

        max_mb = self._config.get("max_file_size_mb", 50)
        max_bytes = max_mb * 1024 * 1024
        added, updated, deleted, skipped = [], [], [], []

        for item in items:
            if "deleted" in item:
                deleted.append({"locator": item["id"], "title": item.get("name", "")})
                continue
            if "folder" in item:
                continue  # folders are traversed implicitly by delta
            name = item.get("name", "")
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext not in SUPPORTED_EXTENSIONS:
                skipped.append({"locator": item["id"], "reason": f"unsupported format: {ext or 'no extension'}"})
                continue
            if item.get("size", 0) > max_bytes:
                skipped.append({"locator": item["id"], "reason": f"file too large: {item['size'] // (1024*1024)} MB > {max_mb} MB"})
                continue
            download_url = item.get("@microsoft.graph.downloadUrl")
            if not download_url:
                skipped.append({"locator": item["id"], "reason": "no download URL"})
                continue
            content = self.download(download_url)
            entry = {"locator": item["id"], "title": name, "content": content,
                     "media_type": ext.lstrip(".")}
            # delta with a cursor: items are changes; without: all are new
            (updated if delta_link else added).append(entry)

        return {"added": added, "updated": updated, "deleted": deleted,
                "skipped": skipped, "delta_link": new_link}


class SharePointSource(GraphBase):
    type = "sharepoint"

    def __init__(self, auth, site_id: str) -> None:
        super().__init__(auth)
        self.site_id = site_id

    def files(self) -> list[dict]:
        result = self._get(f"/sites/{self.site_id}/drive/root/children")
        return [
            {
                "locator": item["id"],
                "title": item["name"],
                "download_url": item.get("@microsoft.graph.downloadUrl"),
            }
            for item in result["items"]
            if "file" in item
        ]
