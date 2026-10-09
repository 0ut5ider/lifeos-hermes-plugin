# ABOUTME: Runs the native Algorithm summary button against the configured private FlashNext route.
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
import test_memory_algorithm_jobs as fixtures
from lifeos_hook_bridge.memory_context import route_identity

root = Path(__file__).resolve().parent
record = {'server_mutation': False, 'isolated_synthetic_profile': True, 'status': 'FAIL'}
fixture = fixtures.MemoryAlgorithmJobRelayTests()
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
            tools = [tool.get('function', {}).get('name') for tool in body.get('tools', [])]
            tool_messages = [message for message in body.get('messages', []) if message.get('role') == 'tool']
            wire.append({'path': self.path, 'requested_model': body.get('model'),
                'reasoning_effort': body.get('reasoning_effort'), 'max_tokens': body.get('max_tokens'),
                'finish_reasons': [choice.get('finish_reason') for choice in decoded.get('choices', [])], 'effort_fields': {key: body[key] for key in ('reasoning_effort', 'reasoning', 'extra_body', 'thinking', 'output_config') if key in body}, 'body_keys': sorted(body), 'upstream_status': status_code,
                'tool_names': tools, 'tool_result_count': len(tool_messages),
                'tool_results': [{'call_id': message.get('tool_call_id'), 'content': message.get('content')} for message in tool_messages],
                'prior_tool_call_names': [call.get('function', {}).get('name') for message in body.get('messages', []) for call in message.get('tool_calls', [])],
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
    selected['model'] = {**model, 'streaming': False, 'context_length': 131072}
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
    owner_program = profile / 'plugins/lifeos-hook-bridge/memory_owner_jobs.py'
    owner_receipt = profile / 'actual-owner-job-result.json'
    with owner_program.open('a') as stream:
        stream.write('\n_actual_owner_run=OwnerJobs.run\n'
            'def _observed_owner_run(*args,**kwargs):\n'
            '    result=_actual_owner_run(*args,**kwargs)\n'
            '    Path(' + repr(str(owner_receipt)) + ').write_text(json.dumps(result))\n'
            '    return result\nOwnerJobs.run=_observed_owner_run\n')
    started_at = time.monotonic()
    with httpx.Client(timeout=45) as client:
        fixture.login(client)
        started = client.post(fixture.native + '/api/algorithm-tab/summary/regenerate')
        if started.status_code != 202: raise RuntimeError('The actual Algorithm button refuses the configured build')
        deadline = time.monotonic() + 565
        while not owner_receipt.exists() and time.monotonic() < deadline:
            time.sleep(0.5)
        if not owner_receipt.exists(): raise RuntimeError('The actual owner job does not finish')
        receipt = json.loads(owner_receipt.read_text())
        result = client.get(fixture.native + '/api/algorithm-tab')
    cache = fixture.root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json'
    record.update(elapsed_seconds=time.monotonic()-started_at, selected_job_status=receipt['status'],
        native_status=result.status_code, cache_exists=cache.exists(),
        configured_pin=settings['pinned_tier'],
        configured_efforts={name:settings[name+'_effort'] for name in ('haiku','sonnet','opus','fable')},
        wire_requests=wire)
    if cache.exists():
        value=json.loads(cache.read_text())
        record.update(cache_mode=oct(cache.stat().st_mode & 0o777),
            artifact_sha256=hashlib.sha256(cache.read_bytes()).hexdigest(),
            card_ids=sorted(value['files']), cards=value['files'], overview=value['overview'])
    if receipt['status'] != 'completed': raise RuntimeError('The actual owner job does not complete')
    if result.status_code != 200 or not cache.exists(): raise RuntimeError('The actual Algorithm summary is unavailable')
    if cache.stat().st_mode & 0o777 != 0o600: raise RuntimeError('The Algorithm summary cache is not private')
    if not value['files'] or not value['overview'] or not value['overview']['markdown'].strip():
        raise RuntimeError('The Algorithm job does not produce card and overview text')
    if not wire or any(item['upstream_status'] != 200 or item['requested_model'] != model['default'] for item in wire):
        raise RuntimeError('The native job does not preserve successful private model routing')
    if [item['reasoning_effort'] for item in wire] != [settings['haiku_effort']]*len(value['files']) + [settings['opus_effort']]:
        raise RuntimeError('The actual card and overview requests change the selected tier efforts')
    record.update(status='PASS', observer_forwards_actual_response=True)
    status=0
except Exception as error:
    record.update(failure_type=type(error).__name__,failure=str(error) if isinstance(error,RuntimeError) else 'The isolated private model probe fails',wire_requests=wire if 'wire' in globals() else [])
finally:
    fixture.doCleanups()
    (root / 'algorithm-job-private-model.json').write_text(json.dumps(record,indent=2)+'\n')
    (root / 'algorithm-job-private-model.done').write_text(str(status)+'\n')
    print(json.dumps({key:value for key,value in record.items() if key not in ('wire_requests','cards','overview')}))
sys.exit(status)
