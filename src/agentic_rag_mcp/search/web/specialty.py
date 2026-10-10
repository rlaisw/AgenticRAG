"""Specialty web search (spec 005): profile-scoped domain search.

Profiles live in a user-managed JSON file, hot-reloaded on every call.
Query construction uses `site:` operators through the existing provider chain;
results are post-filtered by substring domain match (FR-006).
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


def _default_path() -> Path:
    return Path.home() / ".config" / "agentic-rag-mcp" / "specialty_profiles.json"


def load_profiles(path: Path | str | None = None, *, return_error: bool = False):
    """Read the profiles JSON per call (hot-reload — FR-001/002).

    Returns the profiles dict, or ({} , error_message) if return_error=True.
    """
    p = Path(path) if path else _default_path()
    if not p.is_file():
        if return_error:
            return {}, f"no specialty profiles configured (file not found: {p})"
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        if return_error:
            return {}, f"specialty profiles file is invalid JSON: {exc}"
        return {}
    if not isinstance(raw, dict):
        if return_error:
            return {}, "specialty profiles file must be a JSON object of profiles"
        return {}
    if return_error:
        return raw, None  # success: no error
    return raw


def normalize_site(entry: str) -> str:
    """Strip scheme, path, leading www.; lowercase (research.md D5)."""
    s = entry.strip().lower()
    if "://" in s:
        s = urlparse(s).netloc or s.split("://", 1)[1]
    s = s.split("/")[0]
    if s.startswith("www."):
        s = s[4:]
    return s


def resolve_profile(profiles: dict, name: str) -> dict:
    """Case-insensitive lookup (FR-003). Returns the profile dict or an error dict."""
    for key, val in profiles.items():
        if key.lower() == name.lower():
            sites = [normalize_site(s) for s in val.get("sites", [])]
            if not sites:  # FR-008
                return {"error": f"profile '{key}' has no sites configured"}
            return {"name": key, "sites": sites,
                    "description": val.get("description", "")}
    available = {k: v.get("description", "") for k, v in profiles.items()}  # FR-007
    return {"error": f"profile '{name}' not found", "available": available}


def construct_scoped_query(sites: list[str], query: str) -> str:
    """Build 'site:a OR site:b <query>' (research.md D3, decided in Clarifications)."""
    scopes = " OR ".join(f"site:{s}" for s in sites)
    return f"{scopes} {query}"


def filter_by_domains(results: list[dict], sites: list[str]) -> list[dict]:
    """Keep only results whose URL contains a configured domain (substring — FR-006)."""
    return [h for h in results if any(s in h.get("url", "") for s in sites)]
