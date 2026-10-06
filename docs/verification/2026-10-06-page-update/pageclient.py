# ABOUTME: Calls the LifeOS plugin page API through a real Hermes dashboard password session.
# ABOUTME: Reuses one private session cookie file so polling stays under the login rate limit.
import json, os, sys, urllib.request, urllib.error
from pathlib import Path
BASE = 'http://127.0.0.1:9119'
settings = dict(line.split('=', 1) for line in
    (Path.home() / '.config/lifeos-acceptance/dashboard.env').read_text().split())
cookies = {}
opener = urllib.request.build_opener()
def call(method, path, body=None, origin=True):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        request.add_header('Content-Type', 'application/json')
    if cookies:
        request.add_header('Cookie', '; '.join(f'{k}={v}' for k, v in cookies.items()))
    if origin:
        request.add_header('Origin', BASE)
    try:
        with opener.open(request, timeout=1800) as response:
            for header in response.headers.get_all('Set-Cookie') or []:
                name, value = header.split(';', 1)[0].split('=', 1)
                cookies[name.strip()] = value.strip()
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()
session = Path.home() / '.config/lifeos-acceptance/session.json'
if session.is_file():
    cookies.update(json.loads(session.read_text()))
def login():
    cookies.clear()
    status, text = call('POST', '/auth/password-login', {'provider': 'basic',
        'username': settings['HERMES_DASHBOARD_BASIC_AUTH_USERNAME'],
        'password': settings['HERMES_DASHBOARD_BASIC_AUTH_PASSWORD']})
    if status != 200:
        sys.exit(f'login failed: {status}')
method, path = sys.argv[1], sys.argv[2]
body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
if not cookies:
    login()
status, text = call(method, '/api/plugins/lifeos-hook-bridge' + path, body)
if status == 401:
    login()
    status, text = call(method, '/api/plugins/lifeos-hook-bridge' + path, body)
session.touch(mode=0o600)
session.write_text(json.dumps(cookies))
print(json.dumps({'method': method, 'path': path, 'status': status,
                  'body': (json.loads(text) if text.strip().startswith(('{', '[')) else text)}, indent=1))
