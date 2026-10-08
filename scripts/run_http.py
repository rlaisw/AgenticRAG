"""Run streamable-HTTP on port 8811 (for Dify / any MCP-over-HTTP host)."""
from agentic_rag_mcp.config import load_config
from agentic_rag_mcp.server import build_server

build_server(load_config()).run(transport="streamable-http")
