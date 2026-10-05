"""Local-folder connector: watch/add/remove with per-file failure isolation."""

from __future__ import annotations

from pathlib import Path

from ..errors import NotFoundError
from ..ingestion.parsers import ParseSkipped, extract_text


class LocalFolderSource:
    type = "local_folder"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        if not self.path.is_dir():
            raise NotFoundError(f"folder not found: {self.path}")

    def scan(self) -> list[Path]:
        exts = {".pdf", ".docx", ".xlsx", ".pptx", ".mp3", ".wav", ".m4a"}
        return sorted(
            p
            for p in self.path.rglob("*")
            if p.suffix.lower() in exts and not any(part.startswith(".") for part in p.parts)
        )

    def read_item(self, path: Path) -> tuple[str, str]:
        """Returns (extracted_text, media_type). Raises ParseSkipped on failure."""
        return extract_text(path), path.suffix.lower().lstrip(".")


__all__ = ["LocalFolderSource", "ParseSkipped"]
