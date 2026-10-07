# ABOUTME: Checks real HTTP relay behavior for paired private-model response controls.
# ABOUTME: Verifies query preservation, body identity, metadata refusal, and credential exclusion.
import base64
import hashlib
import http.client
import http.server
import json
from pathlib import Path
import tempfile
import threading
import unittest

from scripts.paired_response_server import response_handler


class PairedResponseServerTests(unittest.TestCase):
    def test_native_beta_query_reaches_the_gateway_without_recording_authorization(self):
        requests = []
        response_body = b'{"id":"fixture","content":[{"type":"text","text":"READY"}]}'

        class Gateway(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append((self.path, dict(self.headers),
                    json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)

            def log_message(self, *_):
                pass

        gateway = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
        with tempfile.TemporaryDirectory() as directory:
            environment = Path(directory) / 'model.env'
            environment.write_text(f'ANTHROPIC_BASE_URL=http://127.0.0.1:{gateway.server_port}\n'
                'ANTHROPIC_MODEL=private-fixture\nANTHROPIC_AUTH_TOKEN=private-fixture-token\n')
            environment.chmod(0o600)
            relay = http.server.ThreadingHTTPServer(('127.0.0.1', 0), response_handler(environment))
            relay.observed = []
            threads = [threading.Thread(target=server.serve_forever, daemon=True)
                for server in (gateway, relay)]
            for thread in threads:
                thread.start()
            client = http.client.HTTPConnection('127.0.0.1', relay.server_port)
            body = b'{"model":"lifecycle-fixture","messages":[],"stream":false}'
            try:
                client.request('POST', '/v1/messages?beta=true', body,
                    {'Content-Type': 'application/json', 'Authorization': 'Bearer client-fixture-token',
                     'anthropic-version': '2023-06-01'})
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), response_body)
                self.assertEqual(requests[0][0], '/v1/messages?beta=true')
                self.assertEqual(requests[0][1]['Authorization'], 'Bearer private-fixture-token')
                self.assertEqual(requests[0][1]['anthropic-version'], '2023-06-01')
                self.assertEqual(requests[0][2], {'model': 'private-fixture', 'messages': [], 'stream': False})
                recorded = relay.observed[0]
                self.assertEqual(base64.b64decode(recorded['body_base64']), body)
                self.assertEqual(recorded['body_sha256'], hashlib.sha256(body).hexdigest())
                self.assertEqual(base64.b64decode(recorded['response_body_base64']), response_body)
                self.assertNotIn('fixture-token', json.dumps(relay.observed))
                client.request('POST', '/api/show', b'{"name":"lifecycle-fixture"}',
                    {'Content-Type': 'application/json'})
                response = client.getresponse()
                self.assertEqual(response.status, 401)
                self.assertIn(b'METADATA_PROBE_REFUSED', response.read())
                self.assertEqual(len(requests), 1)
            finally:
                client.close()
                for server in (relay, gateway):
                    server.shutdown()
                    server.server_close()
                for thread in threads:
                    thread.join(timeout=10)


if __name__ == '__main__':
    unittest.main()
