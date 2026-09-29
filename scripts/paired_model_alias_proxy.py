# ABOUTME: Lets a disposable Claude Code control advertise a Claude tier while using a private local model.
# ABOUTME: Rewrites only the model field and never records request bodies or authorization headers.

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


_HOP_HEADERS = frozenset({"connection", "content-length", "host", "transfer-encoding"})


def make_handler(upstream_host: str, upstream_port: int, actual_model: str):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 10_485_760:
                    raise ValueError("Request size is invalid")
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict) or not isinstance(request.get("model"), str):
                    raise ValueError("Model is missing")
            except (ValueError, UnicodeError):
                self.send_error(400)
                return
            request["model"] = actual_model
            body = json.dumps(request, separators=(",", ":")).encode()
            headers = {key: value for key, value in self.headers.items()
                       if key.lower() not in _HOP_HEADERS}
            headers["Content-Length"] = str(len(body))
            sent = False
            try:
                connection = http.client.HTTPConnection(upstream_host, upstream_port, timeout=90)
                connection.request("POST", self.path, body=body, headers=headers)
                response = connection.getresponse()
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in _HOP_HEADERS:
                        self.send_header(key, value)
                self.send_header("Connection", "close")
                self.end_headers()
                sent = True
                while chunk := response.read(65_536):
                    self.wfile.write(chunk)
                connection.close()
            except (OSError, http.client.HTTPException):
                if not sent:
                    self.send_error(502)

        def log_message(self, *_: object) -> None:
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite a Claude model alias for a private local gateway")
    parser.add_argument("listen_port", type=int)
    parser.add_argument("upstream_host")
    parser.add_argument("upstream_port", type=int)
    parser.add_argument("actual_model")
    args = parser.parse_args()
    address = ipaddress.ip_address(args.upstream_host)
    if not address.is_private:
        parser.error("The upstream host must have a private IP address")
    ThreadingHTTPServer(("127.0.0.1", args.listen_port),
                        make_handler(args.upstream_host, args.upstream_port, args.actual_model)).serve_forever()


if __name__ == "__main__":
    main()
