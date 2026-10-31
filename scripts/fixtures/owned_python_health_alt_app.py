"""Alternate first-party Python HTTP health fixture for disposable OCI CI only."""
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        body = b"cloudforge-owned-python-alt-ok\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def _stop_on_sigterm(_signum, _frame):
    # PID 1 must install a handler: Linux ignores default-terminated signals there.
    # Raising here avoids HTTPServer.shutdown(), which would deadlock in this thread.
    raise SystemExit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _stop_on_sigterm)
    server = HTTPServer(("127.0.0.1", 8080), HealthHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
