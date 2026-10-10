# ABOUTME: Verifies actual authenticated native Pulse reads and synthetic Content actions.
# ABOUTME: Checks anonymous refusal and current owner revocation in the isolated acceptance profile.
import http.cookiejar
import importlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, installed = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
sys.path.insert(0, str(profile / 'plugins'))
configuration = importlib.import_module('lifeos-hook-bridge.memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
cookie = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(cookie))
anonymous = urllib.request.build_opener(urllib.request.ProxyHandler({}))
observations = []


def request(path, *, method='GET', data=None, authenticated=True, headers=None, dashboard=False):
    url = 'http://127.0.0.1:' + ('18819' if dashboard else '18837') + path
    selected = dict(headers or {})
    if data is not None:
        selected['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
        method=method, headers=selected)
    try:
        response = (client if authenticated else anonymous).open(req, timeout=45)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        wire = response.read(4 * 1024 * 1024 + 1)
        assert len(wire) <= 4 * 1024 * 1024
        body = json.loads(wire)
        result = {'path': path, 'method': method, 'authenticated': authenticated,
            'status': response.status, 'cache_control': response.headers.get('Cache-Control'), 'body': body}
    observations.append(result)
    (stage / 'application-http-progress.json').write_text(json.dumps(observations, indent=2) + '\n')
    return result


routes = ['/api/memory', '/api/wiki', '/api/life/home', '/api/life/health', '/api/life/finances',
    '/api/life/business', '/api/life/growth', '/api/local-intelligence', '/api/assets', '/api/books',
    '/api/atlas', '/api/atlas/insights', '/api/algorithm-tab', '/api/telos/freshness/summary',
    '/api/content', '/api/conduit/status']
for path in routes:
    result = request(path, authenticated=False)
    if path == '/api/life/growth':
        assert result['status'] == 200 and result['body']['installed'] is False, result
        assert result['body']['newsletter'] is result['body']['youtube'] is result['body']['web'] is None
    else:
        assert result['status'] == 401 and result['cache_control'] == 'no-store', result
login = request('/auth/password-login', method='POST', dashboard=True, data={
    'provider': 'basic', 'username': 'acceptance-owner',
    'password': 'synthetic-application-acceptance-password'})
assert login['status'] == 200
for path in routes:
    result = request(path)
    if path == '/api/local-intelligence':
        assert result['status'] == 404 and result['body']['error'] == 'not_yet_generated', result
    else:
        assert result['status'] == 200, result
    if path != '/api/life/growth':
        assert result['cache_control'] == 'no-store', result

ledger = installed / 'LIFEOS/MEMORY/STATE/content-pipeline/events.jsonl'
source = installed.parent / 'Recordings/Inbox/daily-installed-synthetic.wav'
sidecar = Path(str(source) + '.md')
artifact = installed / 'LIFEOS/MEMORY/STATE/content-pipeline/artifacts/dailysynthetic4109/transcript.md'
for path in (source, sidecar, artifact):
    assert not path.exists(), 'The synthetic action fixture already exists'
source.parent.mkdir(parents=True, exist_ok=True)
source.write_bytes(b'Synthetic Content disposal fixture. No audio decoding is requested.\n')
sidecar.write_text('Synthetic Content sidecar.\n')
artifact.parent.mkdir(parents=True, exist_ok=True)
artifact.write_text('Synthetic Content derivative fixture.\n')
ledger.parent.mkdir(parents=True, exist_ok=True)
row = {'v': 1, 'ts': datetime.now(timezone.utc).isoformat(), 'id': 'dailysynthetic4109',
    'op': 'upsert', 'src': 'synthetic-acceptance', 'fields': {'id': 'dailysynthetic4109',
    'title': 'Synthetic installed Content acceptance', 'path': str(source),
    'created': datetime.now(timezone.utc).isoformat(), 'stage': 'inbox',
    'stage_status': 'pending', 'requested_run': None}}
with ledger.open('a') as stream:
    stream.write(json.dumps(row) + '\n')
before = ledger.read_bytes()
for method, path in [('POST', '/api/content/dailysynthetic4109/run'),
    ('DELETE', '/api/content/dailysynthetic4109')]:
    result = request(path, method=method, authenticated=False)
    assert result['status'] == 401 and result['cache_control'] == 'no-store'
    assert ledger.read_bytes() == before and source.exists() and artifact.exists()
result = request('/api/content/dailysynthetic4109/run', method='POST')
assert result['status'] == 200 and result['body']['requested_run'] == 'regular', result
after_run = ledger.read_bytes()
assert after_run.startswith(before)
result = request('/api/content/dailysynthetic4109/run', method='POST')
assert result['status'] == 200 and result['body']['already'] is True, result
assert ledger.read_bytes() == after_run
board = request('/api/content')
item = next(item for item in board['body']['items'] if item['id'] == 'dailysynthetic4109')
assert item['requested_run'] == 'regular'
result = request('/api/content/dailysynthetic4109', method='DELETE')
assert result['status'] == 200 and result['body'] == {'ok': True, 'id': 'dailysynthetic4109',
    'trashed': 2, 'artifactsRemoved': True, 'runnerKicked': False}, result
assert not source.exists() and not sidecar.exists() and not artifact.parent.exists()
assert (source.parent / '.trash' / source.name).read_bytes().startswith(b'Synthetic Content disposal fixture.')
after_delete = ledger.read_bytes()
result = request('/api/content/dailysynthetic4109', method='DELETE')
assert result['status'] == 404 and ledger.read_bytes() == after_delete, result
assert all(item['id'] != 'dailysynthetic4109' for item in request('/api/content')['body']['items'])

account = 'dashboard:basic:acceptance-owner'
binding = configuration.load()['accounts'][account]
configuration.update(lambda value: value['accounts'].pop(account))
try:
    for path in ('/api/memory', '/api/content'):
        result = request(path)
        assert result['status'] == 403 and result['cache_control'] == 'no-store', result
finally:
    configuration.update(lambda value: value['accounts'].update({account: binding}))
assert request('/api/memory')['status'] == 200
report = {'status': 'PASS', 'native_reads_verified': len(routes), 'observations': observations,
    'content_run_intent_and_repeat_verified': True, 'content_disposal_and_repeat_verified': True,
    'current_owner_revocation_and_restoration_verified': True, 'synthetic_data_only': True,
    'media_processing_verified': False, 'browser_interactions_verified': False,
    'live_profile_changed': False}
(stage / 'application-http-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'observations'}, indent=2))
