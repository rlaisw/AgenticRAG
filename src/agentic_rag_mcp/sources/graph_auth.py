"""MSAL helper for per-user delegated Microsoft Graph auth (clarification Q4)."""

from __future__ import annotations

import json
from pathlib import Path

from ..errors import SourceAuthError

SCOPES = ["Files.Read", "Sites.Read.All", "offline_access"]


class GraphAuth:
    def __init__(self, client_id: str, cache_path: Path) -> None:
        import msal

        self._cache = msal.SerializableTokenCache()
        self._cache_path = cache_path
        if cache_path.exists():
            self._cache.deserialize(cache_path.read_text())
        self._app = msal.PublicClientApplication(
            client_id,
            authority="https://login.microsoftonline.com/common",
            token_cache=self._cache,
        )

    def _persist(self) -> None:
        if self._cache.has_state_changed:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(self._cache.serialize())

    def token(self) -> str:
        accounts = self._app.get_accounts()
        result = None
        if accounts:
            result = self._app.acquire_token_silent(SCOPES, account=accounts[0])
        if not result:
            raise SourceAuthError(
                "Microsoft sign-in required", context={"action": "run device sign-in"}
            )
        self._persist()
        return result["access_token"]

    def device_sign_in(self) -> dict:
        flow = self._app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise SourceAuthError("device flow failed to start")
        # Caller relays flow["message"] (URL + code) to the user.
        result = self._app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise SourceAuthError("sign-in incomplete", context=result.get("error_description", {}))
        self._persist()
        return {"ok": True}
