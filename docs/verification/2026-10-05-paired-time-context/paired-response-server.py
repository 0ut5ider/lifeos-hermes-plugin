# ABOUTME: Relays synthetic paired client requests to the configured private model gateway.
# ABOUTME: Records body identities and response status without recording authorization headers.
import base64
import hashlib
import http.client
import http.server
import ipaddress
import json
from pathlib import Path
import shlex
from urllib.parse import urlsplit


def model_environment(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError('The private model environment must be a private regular file')
    values = {}
    for line in path.read_text().splitlines():
        for part in shlex.split(line):
            if '=' in part:
                key, value = part.split('=', 1)
                if key in values:
                    raise ValueError('The private model environment repeats a field')
                values[key] = value
    endpoint = urlsplit(values['ANTHROPIC_BASE_URL'])
    if (endpoint.scheme != 'http' or not ipaddress.ip_address(endpoint.hostname).is_private
            or endpoint.path not in ('', '/') or endpoint.query or endpoint.fragment or endpoint.username):
        raise ValueError('The response control requires the private HTTP gateway root')
    if not values.get('ANTHROPIC_MODEL') or not values.get('ANTHROPIC_AUTH_TOKEN'):
        raise ValueError('The response control requires a configured model and authorization')
    return endpoint, values['ANTHROPIC_MODEL'], values['ANTHROPIC_AUTH_TOKEN']


def response_handler(environment_path):
    endpoint, model, authorization = model_environment(environment_path)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            request = json.loads(body)
            record = {'path': self.path, 'body': request, 'body_base64': base64.b64encode(body).decode(),
                'body_sha256': hashlib.sha256(body).hexdigest()}
            self.server.observed.append(record)
            if urlsplit(self.path).path not in ('/v1/messages', '/v1/chat/completions'):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error":{"type":"authentication_error","message":"METADATA_PROBE_REFUSED"}}')
                return
            request = {**request, 'model': model}
            headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authorization}
            for name in ('anthropic-version', 'anthropic-beta'):
                if name in self.headers:
                    headers[name] = self.headers[name]
            connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=90)
            try:
                connection.request('POST', self.path, json.dumps(request).encode(), headers)
                response = connection.getresponse()
                data = response.read()
                record.update(upstream_status=response.status,
                    response_body_sha256=hashlib.sha256(data).hexdigest(),
                    response_body_base64=base64.b64encode(data).decode(), actual_model=model)
                self.send_response(response.status)
                self.send_header('Content-Type', response.getheader('Content-Type', 'application/json'))
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            finally:
                connection.close()

        def log_message(self, *_):
            pass

    return Handler
