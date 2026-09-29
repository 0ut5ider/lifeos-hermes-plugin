# ABOUTME: Verifies the disposable model alias proxy against a real loopback HTTP server.
# ABOUTME: Checks that only the model changes and an event stream reaches the caller.

import http.client
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scripts.paired_model_alias_proxy import make_handler


class PairedModelAliasProxyTests(unittest.TestCase):
    def test_forwards_private_request_with_only_model_rewritten(self):
        received = []

        class Upstream(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                received.append((self.path, json.loads(body), self.headers.get("x-api-key")))
                payload = b"data: {\"type\":\"message_stop\"}\n\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_):
                pass

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        proxy = ThreadingHTTPServer(("127.0.0.1", 0),
                                    make_handler("127.0.0.1", upstream.server_port, "local-model"))
        threads = [threading.Thread(target=server.serve_forever, daemon=True)
                   for server in (upstream, proxy)]
        for thread in threads:
            thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", proxy.server_port, timeout=5)
            request = {"model": "claude-haiku-4-5", "stream": True,
                       "messages": [{"role": "user", "content": "READY"}]}
            connection.request("POST", "/v1/messages", body=json.dumps(request).encode(),
                               headers={"Content-Type": "application/json", "x-api-key": "test-only"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Content-Type"), "text/event-stream")
            self.assertEqual(response.read(), b"data: {\"type\":\"message_stop\"}\n\n")
            connection.close()
            self.assertEqual(received, [
                ("/v1/messages", {**request, "model": "local-model"}, "test-only")
            ])
        finally:
            for server in (proxy, upstream):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
