"""First-party reference application for the owned-process demo.

Only an ephemeral numeric loopback listener is permitted. This is not a
sandbox for arbitrary user code, a deployment adapter, or a cloud service.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(204 if self.path == "/health" else 404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self.send_response(405)
        self.end_headers()

    def log_message(self, *_args):
        pass


def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    try:
        # The parent receives only an ephemeral numeric port, never credentials.
        print(server.server_port, flush=True)
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
