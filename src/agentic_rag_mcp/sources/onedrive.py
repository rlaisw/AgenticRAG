"""Microsoft Graph base for OneDrive / SharePoint connectors (FR-003).

Requires MSAL delegated auth (GraphAuth). Failures raise SourceAuthError or
ProviderError so the pipeline marks the source degraded and continues.
"""

from __future__ import annotations

import httpx

from ..errors import ProviderError, SourceAuthError

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphBase:
    type = "graph"

    def __init__(self, auth) -> None:
        self._auth = auth

    def _get(self, url: str, params: dict | None = None) -> dict:
        try:
            token = self._auth.token()
        except SourceAuthError:
            raise
        try:
            resp = httpx.get(
                f"{GRAPH}{url}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
                timeout=15.0,
            )
            if resp.status_code in (401, 403):
                raise SourceAuthError(f"graph auth failed: {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except SourceAuthError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"graph request failed: {exc}") from exc


class OneDriveSource(GraphBase):
    type = "onedrive"

    def files(self) -> list[dict]:
        data = self._get("/me/drive/root/children")
        return [
            {
                "locator": item["id"],
                "title": item["name"],
                "download_url": item.get("@microsoft.graph.downloadUrl"),
            }
            for item in data.get("value", [])
            if "file" in item
        ]


class SharePointSource(GraphBase):
    type = "sharepoint"

    def __init__(self, auth, site_id: str) -> None:
        super().__init__(auth)
        self.site_id = site_id

    def files(self) -> list[dict]:
        data = self._get(f"/sites/{self.site_id}/drive/root/children")
        return [
            {
                "locator": item["id"],
                "title": item["name"],
                "download_url": item.get("@microsoft.graph.downloadUrl"),
            }
            for item in data.get("value", [])
            if "file" in item
        ]
