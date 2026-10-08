"""Run an SSE-transport instance on port 8812 (for Dify mcp_sse plugin)."""
from agentic_rag_mcp.config import load_config
from agentic_rag_mcp.server import build_server

cfg = load_config()
cfg.mcp_port = 8812
build_server(cfg).run(transport="sse")
