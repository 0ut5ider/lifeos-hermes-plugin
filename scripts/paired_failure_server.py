# ABOUTME: Returns a fixed local API failure for paired StopFailure hook runs.
# ABOUTME: Does not log request bodies or forward requests outside loopback.

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length", "0"))
        if size:
            self.rfile.read(size)
        body = json.dumps({"error": {"type": "authentication_error", "message": "PAIR_FAILURE_212"}}).encode()
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 31355), Handler).serve_forever()
