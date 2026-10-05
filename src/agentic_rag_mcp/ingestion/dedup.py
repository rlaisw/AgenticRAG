"""Content-hash dedup (FR-006). SHA-256 of normalized extracted text."""

from __future__ import annotations

import hashlib
import re

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WS.sub(" ", text).strip().casefold()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()
