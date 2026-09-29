# ABOUTME: Checks that the HTTP trace proxy preserves hook request and response behavior.
# ABOUTME: Confirms the public trace metadata does not store the request body.

import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.paired_http_trace import make_handler


class PairedHttpTraceTests(unittest.TestCase):
    def test_relays_hook_and_logs_only_metadata(self):
        received = []

        class Upstream(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"OK")

            def log_message(self, *_):
                pass

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
            proxy = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(upstream.server_port, trace))
            threads = [threading.Thread(target=server.serve_forever, daemon=True)
                       for server in (upstream, proxy)]
            for thread in threads:
                thread.start()
            try:
                payload = b'{"hook_event_name":"PreToolUse","tool_name":"Skill","prompt":"private marker"}'
                request = urllib.request.Request(
                    f"http://127.0.0.1:{proxy.server_port}/hooks/skill-guard",
                    data=payload, headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=3) as response:
                    self.assertEqual(response.read(), b"OK")
                    self.assertEqual(response.status, 200)
                self.assertEqual(received, [payload])
                saved = trace.read_text()
                self.assertNotIn("private marker", saved)
                row = json.loads(saved)
                self.assertEqual(row["tool_name"], "Skill")
                self.assertEqual(row["response_size"], 2)
            finally:
                for server in (proxy, upstream):
                    server.shutdown()
                    server.server_close()
                for thread in threads:
                    thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
