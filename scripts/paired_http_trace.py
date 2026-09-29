# ABOUTME: Relays disposable LifeOS HTTP hooks to an isolated Pulse server.
# ABOUTME: Records hook request and response metadata without storing prompt text.

from __future__ import annotations

import argparse
import fcntl
import hashlib
import http.client
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOOK_PATHS = frozenset({"/hooks/skill-guard", "/hooks/agent-guard"})


def make_handler(upstream_port: int, trace_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path not in HOOK_PATHS:
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if length < 0 or length > 1_048_576:
                self.send_error(413)
                return
            request = self.rfile.read(length)
            try:
                upstream = http.client.HTTPConnection("127.0.0.1", upstream_port, timeout=15)
                upstream.request("POST", self.path, body=request,
                                 headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
                response = upstream.getresponse()
                status = response.status
                body = response.read(1_048_577)
                content_type = response.getheader("Content-Type", "application/json")
                upstream.close()
            except (OSError, http.client.HTTPException):
                status, body, content_type = 502, b"Pulse hook unavailable", "text/plain"
            try:
                payload = json.loads(request)
            except (ValueError, UnicodeError):
                payload = {}
            row = {"time_ns": time.time_ns(), "path": self.path,
                   "event": payload.get("hook_event_name"),
                   "tool_name": payload.get("tool_name"),
                   "session_id": payload.get("session_id"),
                   "request_sha256": hashlib.sha256(request).hexdigest(),
                   "response_sha256": hashlib.sha256(body).hexdigest(),
                   "response_size": len(body), "status": status}
            descriptor = os.open(trace_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                os.write(descriptor, (json.dumps(row) + "\n").encode())
            finally:
                os.close(descriptor)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Trace isolated LifeOS HTTP hook calls")
    parser.add_argument("listen_port", type=int)
    parser.add_argument("upstream_port", type=int)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    if not args.trace.is_absolute() or args.trace.is_symlink():
        parser.error("Trace must be an absolute regular path")
    ThreadingHTTPServer(("127.0.0.1", args.listen_port),
                        make_handler(args.upstream_port, args.trace)).serve_forever()


if __name__ == "__main__":
    main()
