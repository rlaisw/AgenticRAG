"""Specialty search (FR-001..FR-009; research.md D1-D6):
profile loading (hot-reload, case-insensitive, error tolerance), site normalization,
query construction (site: prefix), domain post-filter (substring match)."""

import json
from pathlib import Path

import pytest

from agentic_rag_mcp.search.web.specialty import (
    filter_by_domains, load_profiles, normalize_site,
    resolve_profile, construct_scoped_query,
)


@pytest.fixture
def profiles_file(tmp_path):
    p = tmp_path / "specialty_profiles.json"
    p.write_text(json.dumps({
        "microsoft": {"sites": ["learn.microsoft.com", "techcommunity.microsoft.com"],
                       "description": "Microsoft docs"},
        "security": {"sites": ["owasp.org", "nist.gov"],
                      "description": "Security standards"},
        "Empty": {"sites": [], "description": "No sites"},
    }))
    return p


def test_load_profiles_valid_file(profiles_file):
    profiles = load_profiles(profiles_file)
    assert set(profiles.keys()) == {"microsoft", "security", "Empty"}
    assert profiles["microsoft"]["description"] == "Microsoft docs"
    assert "learn.microsoft.com" in profiles["microsoft"]["sites"]


def test_load_profiles_missing_file(tmp_path):
    profiles, error = load_profiles(tmp_path / "nonexistent.json", return_error=True)
    assert profiles == {}
    assert "not found" in error.lower()          # FR-004: honest error


def test_load_profiles_malformed_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    profiles, error = load_profiles(p, return_error=True)
    assert profiles == {}
    assert "invalid json" in error.lower()       # FR-004


def test_resolve_profile_case_insensitive(profiles_file):
    profiles = load_profiles(profiles_file)
    assert resolve_profile(profiles, "Microsoft") is not None    # FR-003
    assert resolve_profile(profiles, "MICROSOFT") is not None
    assert resolve_profile(profiles, "microsoft") is not None


def test_resolve_profile_not_found_returns_available(profiles_file):
    profiles = load_profiles(profiles_file)
    result = resolve_profile(profiles, "nonexistent")
    assert result["error"] and "nonexistent" in result["error"]  # FR-007
    assert "available" in result and "microsoft" in result["available"]


def test_resolve_profile_empty_sites_error(profiles_file):
    profiles = load_profiles(profiles_file)
    result = resolve_profile(profiles, "Empty")
    assert result["error"] and "no sites" in result["error"].lower()  # FR-008


def test_normalize_site_strips_scheme_path_www():
    assert normalize_site("https://learn.microsoft.com/exchange/dkim") == "learn.microsoft.com"
    assert normalize_site("http://www.owasp.org") == "owasp.org"
    assert normalize_site("HTTPS://NIST.GOV") == "nist.gov"
    assert normalize_site("docs.python.org/") == "docs.python.org"
    assert normalize_site("docs.python.org") == "docs.python.org"  # already clean


def test_construct_scoped_query_multiple_sites():
    q = construct_scoped_query(["learn.microsoft.com", "techcommunity.microsoft.com"], "DKIM")
    assert "site:learn.microsoft.com" in q
    assert "site:techcommunity.microsoft.com" in q
    assert q.endswith("DKIM")
    assert " OR " in q


def test_construct_scoped_query_single_site():
    q = construct_scoped_query(["owasp.org"], "XSS")
    assert q == "site:owasp.org XSS"


def test_filter_by_domains_substring_match():
    """FR-006: parent domain matches subdomains (decided in Clarifications)."""
    results = [
        {"url": "https://learn.microsoft.com/exchange/dkim"},
        {"url": "https://techcommunity.microsoft.com/t/dkim"},
        {"url": "https://randomblog.com/dkim"},
        {"url": "https://support.microsoft.com/help"},
    ]
    filtered = filter_by_domains(results, ["microsoft.com"])
    assert len(filtered) == 3  # randomblog.com filtered out
    assert all("microsoft.com" in h["url"] for h in filtered)


def test_filter_by_domains_empty_input():
    assert filter_by_domains([], ["microsoft.com"]) == []


def test_filter_by_domains_no_matches():
    results = [{"url": "https://example.com/page"}]
    assert filter_by_domains(results, ["microsoft.com"]) == []
