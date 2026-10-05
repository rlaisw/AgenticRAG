"""Configuration loading for agentic-rag-mcp.

Config file: ~/.config/agentic-rag-mcp/config.toml
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "agentic-rag-mcp"
CONFIG_FILE = CONFIG_DIR / "config.toml"
STATE_DB = CONFIG_DIR / "state.sqlite3"
VECTOR_DIR = CONFIG_DIR / "lancedb"

DEFAULT_CONFIG = """\
# agentic-rag-mcp configuration

[embedding]
model = "all-MiniLM-L6-v2"   # local sentence-transformers model
device = "cpu"

[agent]
max_iterations = 5           # deliberative loop budget (FR-014/FR-017)

[decision_layer]
# Laya desktop app local MCP surface; unreachable => heuristic fallback
laya_url = "http://127.0.0.1:8420/mcp/"
laya_token = ""              # from Laya Settings -> MCP

[web]
# order in which providers are tried; providers without config are skipped
fallback_order = ["searxng", "tavily", "exa"]

[web.tavily]
# api_key = ""

[web.exa]
# api_key = ""

[web.searxng]
# url = "http://127.0.0.1:8888"

[features]
graphify = false             # optional graph-search layer

[storage]
# state_db / vector_dir default to ~/.config/agentic-rag-mcp/
"""


@dataclass
class Config:
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    max_iterations: int = 5
    laya_url: str = "http://127.0.0.1:8420/mcp/"
    laya_token: str = ""
    web_fallback_order: list[str] = field(default_factory=lambda: ["searxng", "tavily", "exa"])
    web_tavily_key: str = ""
    web_exa_key: str = ""
    web_searxng_url: str = ""
    graphify_enabled: bool = False
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8811
    state_db: Path = STATE_DB
    vector_dir: Path = VECTOR_DIR
    raw: dict[str, Any] = field(default_factory=dict)


def _get(raw: dict[str, Any], *keys: str, default: Any = None) -> Any:
    node = raw
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def load_config(path: Path | None = None) -> Config:
    path = path or CONFIG_FILE
    raw: dict[str, Any] = {}
    if path.exists():
        raw = tomllib.loads(path.read_text())
    cfg = Config(
        embedding_model=_get(raw, "embedding", "model", default="all-MiniLM-L6-v2"),
        embedding_device=_get(raw, "embedding", "device", default="cpu"),
        max_iterations=int(_get(raw, "agent", "max_iterations", default=5)),
        laya_url=_get(raw, "decision_layer", "laya_url", default="http://127.0.0.1:8420/mcp/"),
        laya_token=_get(raw, "decision_layer", "laya_token", default=""),
        web_fallback_order=_get(
            raw, "web", "fallback_order", default=["searxng", "tavily", "exa"]
        ),
        web_tavily_key=_get(raw, "web", "tavily", "api_key", default=""),
        web_exa_key=_get(raw, "web", "exa", "api_key", default=""),
        web_searxng_url=_get(raw, "web", "searxng", "url", default=""),
        graphify_enabled=bool(_get(raw, "features", "graphify", default=False)),
        mcp_host=_get(raw, "server", "host", default="127.0.0.1"),
        mcp_port=int(_get(raw, "server", "port", default=8811)),
        raw=raw,
    )
    cfg.state_db = Path(_get(raw, "storage", "state_db", default=str(STATE_DB))).expanduser()
    cfg.vector_dir = Path(_get(raw, "storage", "vector_dir", default=str(VECTOR_DIR))).expanduser()
    return cfg


def init_config(path: Path | None = None, force: bool = False) -> Path:
    """Write the default config; returns the config path."""
    path = path or CONFIG_FILE
    if path.exists() and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG)
    return path
