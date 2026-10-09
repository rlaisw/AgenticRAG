"""Integration fixtures: a local HTTP server standing in for the live web.

No network access needed: /normal serves the ordered fixture, /slow delays past
the fetch timeout, /forbidden returns 403, /redirect-private redirects to a
loopback target (SSRF hop case), /oversized serves the oversized fixture.
"""

from __future__ import annotations

import http.server
import threading
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "research"


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 — http.server API
        if self.path == "/normal":
            body = (FIXTURES / "ordered.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/slow":
            import time

            time.sleep(5.0)  # exceeds the reduced test fetch timeout
            self.send_response(200)
            self.end_headers()
        elif self.path == "/forbidden":
            self.send_response(403)
            self.end_headers()
        elif self.path == "/redirect-private":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:9/x")
            self.end_headers()
        elif self.path == "/oversized":
            body = (FIXTURES / "oversized.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # silence request logging in test output
        pass


@pytest.fixture(scope="session")
def fixture_web_server():
    """Serve the research fixtures on a random local port; yields the base URL."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
