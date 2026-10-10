"""AgenticRAG MCP sidecar for Dify: real tools over HTTP.

Bridges the actual agentic-rag-mcp server (LanceDB + embedder + pipeline)
onto a Dify-compatible surface, per the Dify MCP Sidecar procedure:

  - stateless_http=True  -> Dify sends requests without session management
  - POST /mcp            -> Streamable HTTP (recommended for Dify)
  - GET /sse + POST /messages/  -> legacy SSE fallback
  - GET /healthz         -> container health check
  - binds 0.0.0.0:28080  -> reachable via Docker DNS (http://agentic-rag:28080/mcp)

Run locally:  .venv/bin/python dify/docker/mcp-server/server.py
Run in Docker: see Dockerfile next to this file.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make `agentic_rag_mcp` importable when run straight from the repo checkout.
# (In Docker the file is copied to /app and the package is pip-installed,
# so there is no repo root to find — skip path injection there.)
_p = Path(__file__).resolve()
if len(_p.parents) > 3 and (_p.parents[3] / "src" / "agentic_rag_mcp").is_dir():
    sys.path.insert(0, str(_p.parents[3] / "src"))

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from agentic_rag_mcp.config import load_config
from agentic_rag_mcp.server import build_server

HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "28080"))

# stateless_http=True is required so Dify can send stateless requests
# without session-management errors.
mcp = build_server(load_config(), stateless_http=True, host=HOST, port=PORT)

streamable = mcp.streamable_http_app()  # registers POST /mcp, creates session manager
sse = mcp.sse_app()                     # registers GET /sse, POST /messages/


async def healthz(request) -> JSONResponse:
    """Container health check (docker exec ... curl http://agentic-rag:28080/healthz)."""
    return JSONResponse({"status": "ok"})


async def mcp_get(request) -> Response:
    """Browsers/probes that GET /mcp get a clean 405 instead of a confusing
    JSON-RPC 406. Per MCP streamable-HTTP spec, servers without the optional
    server-initiated stream answer 405; clients (incl. Dify) proceed POST-only."""
    return Response(
        "MCP streamable HTTP endpoint. Send JSON-RPC via POST. Health: GET /healthz",
        status_code=405,
        headers={"Allow": "POST"},
    )


@asynccontextmanager
async def lifespan(app):
    # Streamable HTTP needs its session manager started for the app's lifetime.
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/healthz", healthz, methods=["GET"]),
        Route("/mcp", mcp_get, methods=["GET"]),  # before the SDK route: intercepts GET only
        *streamable.routes,
        *sse.routes,
    ],
    lifespan=lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
