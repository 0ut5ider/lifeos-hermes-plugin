# ABOUTME: Runs the native Conduit button against the configured private FlashNext route.
# ABOUTME: Uses an isolated synthetic profile and records no credentials or personal memory.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import threading
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx
from ruamel.yaml import YAML
import test_memory_conduit_jobs as fixtures
from lifeos_hook_bridge.memory_context import route_identity

root = Path(__file__).resolve().parent
record = {'server_mutation': False, 'synthetic_input_only': True, 'status': 'FAIL'}
fixture = fixtures.MemoryConduitJobRelayTests()
status = 1
try:
    # Capture provider configuration in memory. The selected file is not a LifeOS memory record.
    response = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
        'root@192.168.8.252', 'cat /home/lifeos-hermes/.hermes/config.yaml'], capture_output=True, text=True, timeout=12)
    if response.returncode: raise RuntimeError('The configured provider cannot be read')
    configured = YAML(typ='safe').load(response.stdout)
    model = configured['model']
    original_endpoint = model['base_url'].rstrip('/')
    wire = []
    class Forwarder(BaseHTTPRequestHandler):
        def do_POST(self):
            data = self.rfile.read(int(self.headers['Content-Length']))
            body = json.loads(data)
            target = original_endpoint + (self.path.removeprefix('/v1') if original_endpoint.endswith('/v1') else self.path)
            request = urllib.request.Request(target, data=data, headers={'Content-Type': 'application/json',
                'Authorization': self.headers.get('Authorization', '')})
            try: reply = urllib.request.urlopen(request, timeout=180)
            except urllib.error.HTTPError as error: reply = error
            with reply:
                payload = reply.read()
                status_code = reply.status
            decoded = json.loads(payload)
            wire.append({'path': self.path, 'requested_model': body.get('model'),
                'reasoning_effort': body.get('reasoning_effort'), 'effort_fields': {key: body[key] for key in ('reasoning_effort', 'reasoning', 'extra_body', 'thinking', 'output_config') if key in body}, 'body_keys': sorted(body), 'upstream_status': status_code,
                'actual_model': decoded.get('model'), 'response_sha256': hashlib.sha256(payload).hexdigest()})
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *_): pass
    forwarder = ThreadingHTTPServer(('127.0.0.1', 0), Forwarder)
    threading.Thread(target=forwarder.serve_forever, daemon=True).start()
    fixture.addCleanup(forwarder.server_close)
    fixture.addCleanup(forwarder.shutdown)
    # The observer forwards the actual response and changes only the private test endpoint.
    model['base_url'] = f'http://127.0.0.1:{forwarder.server_port}/v1'
    settings = configured['plugins']['entries']['lifeos-hook-bridge']['settings']
    fixture.setUp()
    profile = fixture.fixture.profile
    selected = json.loads((profile / 'config.yaml').read_text())
    selected['model'] = model
    selected['plugins']['entries'] = {'lifeos-hook-bridge': {'settings': settings}}
    selected['plugins']['entries']['lifeos-hook-bridge']['settings']['lifeos_source_dir'] = str(fixture.root)
    path = profile / 'config.yaml'
    path.write_text(json.dumps(selected))
    path.chmod(0o600)
    route = {'provider': model['provider'], 'model': model['default'], 'base_url': model['base_url'],
        'api_mode': model.get('api_mode', 'chat_completions')}
    fixture.fixture.configuration.update(lambda value:
        value['destinations']['terminal:' + str(profile)].update(model_routes=[route_identity(**route)]))
    launcher = fixture.fixture.home / '.local/bin/hermes'
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' -m hermes_cli.main "$@"\n')
    launcher.chmod(0o700)
    date = datetime.now().strftime('%Y-%m-%d')
    events = fixture.root / 'LIFEOS/USER/CONDUIT/events' / (date + '.jsonl')
    events.parent.mkdir(parents=True)
    events.write_text(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'type': 'app-focus',
        'source': 'synthetic', 'app': 'Synthetic Conduit Document Editor',
        'detail': {'intervalSec': 3600}}) + '\n')
    with httpx.Client(timeout=40) as client:
        fixture.login(client)
        started = client.post(fixture.native + '/api/conduit/insight/build')
        if started.status_code != 202: raise RuntimeError('The actual button refuses the configured build')
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            result = client.get(fixture.native + '/api/conduit/insight')
            if result.status_code not in (200, 503): raise RuntimeError('The current insight response refuses unexpectedly')
            if result.status_code == 200 and not result.json()['building']: break
            time.sleep(0.25)
        if result.status_code != 200 or result.json()['building']: raise RuntimeError('The private model build does not finish')
        delivered = result.json()
    artifact = fixture.root / 'LIFEOS/USER/CONDUIT/insights' / (date + '.json')
    value = json.loads(artifact.read_text())
    if value['model'] in ('(none)', '(failed)') or not value['contentTypes'] or not delivered.get('available'):
        raise RuntimeError('The native insight does not contain a successful model result')
    if artifact.stat().st_mode & 0o777 != 0o600: raise RuntimeError('The native insight is not private')
    record.update(wire_requests=wire, configured_pin=settings['pinned_tier'], configured_efforts={name: settings[name + '_effort'] for name in ('haiku','sonnet','opus','fable')})
    if len(wire) != 1 or wire[0]['upstream_status'] != 200 or wire[0]['requested_model'] != model['default']:
        raise RuntimeError('The configured private model does not receive one successful request')
    expected_effort = settings['haiku_effort']
    if wire[0]['reasoning_effort'] != expected_effort: raise RuntimeError('The actual request changes the configured tier effort')
    record.update(status='PASS', native_insight_model=value['model'], requested_native_level=value['level'],
        wire_requests=wire, observer_forwards_actual_response=True,
        pinned_tier=settings['pinned_tier'], tier_efforts={name: settings[name + '_effort']
            for name in ('haiku', 'sonnet', 'opus', 'fable')}, event_count=value['eventsConsidered'],
        content_type_count=len(value['contentTypes']), artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        artifact_mode=oct(artifact.stat().st_mode & 0o777), response_status=result.status_code)
    status = 0
except Exception as error:
    # Report fixed operational errors without model configuration or credential values.
    record['failure_type'] = type(error).__name__
    record['failure'] = str(error) if isinstance(error, RuntimeError) else 'The isolated private model probe fails'
finally:
    fixture.doCleanups()
    (root / 'conduit-job-private-model-current.json').write_text(json.dumps(record, indent=2) + '\n')
    (root / 'conduit-job-private-model-current.done').write_text(str(status) + '\n')
    print(json.dumps(record))
sys.exit(status)
