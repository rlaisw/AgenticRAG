"""Web search provider adapters: Tavily, Exa, self-hosted SearXNG (FR-011).

Adapter contract: `search(query, limit) -> [{title, url, snippet}]`.
Failures raise ProviderError so callers can fall back per SC-005.
"""

from __future__ import annotations

import httpx

from ...errors import ProviderError


class TavilyProvider:
    name = "tavily"

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        if not api_key:
            raise ProviderError("tavily api_key not configured")
        self._key = api_key
        self._timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[dict]:
        try:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={"api_key": self._key, "query": query, "max_results": limit},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"tavily failed: {exc}") from exc
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in data.get("results", [])
        ]


class ExaProvider:
    name = "exa"

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        if not api_key:
            raise ProviderError("exa api_key not configured")
        self._key = api_key
        self._timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[dict]:
        try:
            resp = httpx.post(
                "https://api.exa.ai/search",
                json={"query": query, "num_results": limit, "contents": {"text": True}},
                headers={"x-api-key": self._key},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"exa failed: {exc}") from exc
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("text", "")}
            for r in data.get("results", [])
        ]


class SearxngProvider:
    name = "searxng"

    def __init__(self, url: str, timeout: float = 10.0) -> None:
        if not url:
            raise ProviderError("searxng url not configured")
        self._url = url.rstrip("/")
        self._timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[dict]:
        try:
            resp = httpx.get(
                f"{self._url}/search",
                params={"q": query, "format": "json"},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"searxng failed: {exc}") from exc
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in data.get("results", [])[:limit]
        ]


def build_providers(cfg) -> list:
    """Instantiate configured providers in fallback order."""
    out = []
    for name in cfg.web_fallback_order:
        try:
            if name == "tavily":
                out.append(TavilyProvider(cfg.web_tavily_key))
            elif name == "exa":
                out.append(ExaProvider(cfg.web_exa_key))
            elif name == "searxng":
                out.append(SearxngProvider(cfg.web_searxng_url))
        except ProviderError:
            continue  # unconfigured providers are skipped, not fatal
    return out


def search_all(providers: list, query: str, limit: int = 5):
    """Query every configured engine and aggregate (FR-001/003/004).

    Returns (hits, engines_used, error): hits carry the frozen fields plus the
    contributing `engine`; duplicate URLs are dropped keeping the first ranking;
    a failing engine is skipped, not fatal; error is set only when every
    configured engine failed (or none are configured) — never fabricated hits.
    """
    hits: list[dict] = []
    engines_used: list[str] = []
    failures: list[str] = []
    seen: set[str] = set()
    for provider in providers:
        try:
            returned = provider.search(query, limit=limit)
        except Exception as exc:  # noqa: BLE001 — engine isolation (FR-003)
            failures.append(f"{provider.name}: {exc}")
            continue
        if provider.name not in engines_used:
            engines_used.append(provider.name)
        for hit in returned:
            url = hit.get("url", "")
            if not url or url in seen:  # FR-004: dedup, first ranking wins
                continue
            seen.add(url)
            hits.append({**hit, "engine": provider.name})
    error = None
    if not providers:
        error = {"message": "no web engines configured", "details": []}
    elif failures and not hits and not engines_used:
        error = {"message": "all engines failed", "details": failures}
    return hits[:limit], engines_used, error
