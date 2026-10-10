# ABOUTME: Runs the native LocalIntelligence button against the configured private FlashNext route.
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
import test_memory_local_refresh_jobs as fixtures
from lifeos_hook_bridge.memory_context import route_identity

root = Path(__file__).resolve().parent
record = {'server_mutation': False, 'public_test_location_only': True, 'status': 'FAIL'}
fixture = fixtures.MemoryLocalRefreshJobRelayTests()
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
                'reasoning_effort': body.get('reasoning_effort'), 'effort_fields': {key: body[key] for key in ('reasoning_effort', 'reasoning', 'extra_body', 'thinking', 'output_config') if key in body}, 'body_keys': sorted(body), 'upstream_status': status_code,
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
    child = profile / 'plugins/lifeos-hook-bridge/bin/claude'
    original_child = child.with_name('actual_claude')
    child.rename(original_child)
    child_observation = profile / 'child-call-observation.json'
    child.write_text('#!/usr/bin/env python3\nimport subprocess,sys,json;from pathlib import Path\n'
        'result=subprocess.run([' + repr(str(original_child)) + ',*sys.argv[1:]],input=sys.stdin.buffer.read(),capture_output=True)\n'
        'Path(' + repr(str(child_observation)) + ').write_text(json.dumps({"arguments":sys.argv[1:],"exit_code":result.returncode,"stderr":result.stderr.decode()}))\n'
        'sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr);sys.exit(result.returncode)\n')
    child.chmod(0o700)
    identity = fixture.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
    identity.write_text('- **Hometown:** Austin, TX (ZIP 78701, Travis County)\n')
    with httpx.Client(timeout=40) as client:
        fixture.login(client)
        started = client.post(fixture.native + '/api/local-intelligence/refresh')
        if started.status_code != 202: raise RuntimeError('The actual button refuses the configured build')
        run_id = started.json()['run_id']
        log = fixture.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs' / (run_id + '.log')
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if log.exists() and '[exit] code=' in log.read_text(): break
            time.sleep(0.25)
        if not log.exists() or '[exit] code=' not in log.read_text():
            raise RuntimeError('The native selected job does not finish')
        result = client.get(fixture.native + '/api/local-intelligence')
        delivered = result.json()
    cache = fixture.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/latest.json'
    if child_observation.exists(): record['actual_child'] = json.loads(child_observation.read_text())
    record.update(wire_requests=wire, native_status=result.status_code,
        run_log_characters=len(log.read_text()),
        native_run_log=log.read_text(),
        native_exit_zero='[exit] code=0' in log.read_text(),
        logged_child_failure='claude-fill' in log.read_text(),
        latest_exists=cache.exists(),
        marker_exists=log.with_suffix('.log.started').exists())
    if cache.exists():
        value = json.loads(cache.read_text())
        record['digest_error_count'] = len(value['meta']['errors'])
        record['source_statuses'] = {name: value[name]['source_status'] for name in
            ('construction','crime','business','officials','legislation','elections','arrests','news')}
    model_wire = [item for item in wire if item['path'].endswith('/chat/completions')]
    if not model_wire or any(item['upstream_status'] != 200 for item in model_wire):
        raise RuntimeError('The native research fill does not reach successful private model requests')
    if result.status_code != 200: raise RuntimeError('The native digest is unavailable')
    if cache.stat().st_mode & 0o777 != 0o600: raise RuntimeError('The native digest is not private')
    deadline = time.monotonic() + 15
    while not owner_receipt.exists() and time.monotonic() < deadline: time.sleep(0.1)
    if not owner_receipt.exists(): raise RuntimeError('The selected owner job does not deliver its final result')
    receipt = json.loads(owner_receipt.read_text())
    record['selected_job_status'] = receipt['status']
    if receipt['status'] != 'completed': raise RuntimeError('The selected owner job rejects final delivery')
    states = json.loads((profile / 'lifeos-memory-contexts.json').read_text())
    record['owner_job_input_proof_unchanged'] = all(value.get('user_input') is None for key, value in states.items() if key.startswith('owner-job-'))
    record['separate_research_sessions'] = sum(key.startswith('owner-research-') for key in states)
    if not record['owner_job_input_proof_unchanged'] or record['separate_research_sessions'] != 1:
        raise RuntimeError('Research changes the parent owner-job admission')
    if record.get('actual_child', {}).get('exit_code') != 0 or any('claude-fill:' in error for error in value['meta']['errors']):
        raise RuntimeError('The actual child research fails even though the parent job completes')
    if not any(value[name]['items'] for name in record['source_statuses']):
        raise RuntimeError('The public civic probe produces no useful research items')
    record.update(wire_requests=wire, configured_pin=settings['pinned_tier'],
        configured_efforts={name: settings[name + '_effort'] for name in ('haiku','sonnet','opus','fable')})
    if any(item['requested_model'] != model['default'] for item in model_wire):
        raise RuntimeError('The configured private model does not receive one successful request')
    if any(item['reasoning_effort'] != settings['sonnet_effort'] for item in model_wire):
        raise RuntimeError('The actual request changes the configured tier effort')
    if any(set(item['tool_names']) != {'web_search', 'web_extract'} for item in model_wire):
        raise RuntimeError('The native research request does not preserve the fixed web tool boundary')
    if not any(item['tool_result_count'] > 0 for item in model_wire):
        raise RuntimeError('The actual model does not use a web tool before its final response')
    record.update(status='PASS', requested_native_level='medium', observer_forwards_actual_response=True,
        wire_requests=wire, pinned_tier=settings['pinned_tier'],
        tier_efforts={name: settings[name + '_effort'] for name in ('haiku', 'sonnet', 'opus', 'fable')},
        artifact_sha256=hashlib.sha256(cache.read_bytes()).hexdigest(),
        artifact_mode=oct(cache.stat().st_mode & 0o777), response_status=result.status_code,
        digest_error_count=len(value['meta']['errors']))
    status = 0
except Exception as error:
    # Report fixed operational errors without model configuration or credential values.
    record['failure_type'] = type(error).__name__
    record['failure'] = str(error) if isinstance(error, RuntimeError) else 'The isolated private model probe fails'
finally:
    fixture.doCleanups()
    (root / 'local-job-research-public-after.json').write_text(json.dumps(record, indent=2) + '\n')
    (root / 'local-job-research-public-after.done').write_text(str(status) + '\n')
    print(json.dumps(record))
sys.exit(status)
