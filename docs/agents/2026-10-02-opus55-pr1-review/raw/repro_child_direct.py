# ABOUTME: Reproduces direct child inference sending a forgotten claim past memory admission.
# ABOUTME: Uses the repository native memory fixture and a local synthetic model gateway.
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

sys.path[:0] = ['.', 'tests']
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native_fixture
import test_memory_runtime as runtime_fixture

PROGRAM = Path('lifeos_hook_bridge/bin/claude_direct.py').absolute()
FORGOTTEN = 'Synthetic retired child prompt marker'

fixture = runtime_fixture.MemoryRuntimeTests()
fixture.setUp()
received = []


class Gateway(BaseHTTPRequestHandler):
    def do_POST(self):
        received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        body = json.dumps({'type': 'message', 'content': [{'type': 'text', 'text': 'CHILD-OK'}]}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


server = ThreadingHTTPServer(('127.0.0.1', 0), Gateway)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    base_url = f'http://127.0.0.1:{server.server_port}'
    child = dict(provider='lifeos-local-gateway', model='child-model', base_url=base_url, api_mode='anthropic')
    fixture.configuration['destinations']['chat-a:200']['model_routes'].append(route_identity(**child))
    MemoryConfiguration(fixture.path).save(fixture.configuration)
    saved = fixture.fixture.remember('RULE: ' + FORGOTTEN, 'child-retired', 'principal')
    fixture.fixture.memory.forget(native_fixture.OWNER, saved['reference'], 'child-retired-forget')
    fixture.admit(session='fresh-after-forget')

    control = 'not refused'
    try:
        fixture.runtime.check_call(request={'model': 'child-model', 'system': FORGOTTEN}, **child,
                                   session_id='fresh-after-forget')
    except MemoryAdmissionError as error:
        control = 'refused: ' + str(error)

    environment = {**os.environ, 'HOME': str(fixture.fixture.home), 'HERMES_HOME': str(fixture.home),
                   'ANTHROPIC_BASE_URL': base_url, 'ANTHROPIC_AUTH_TOKEN': 'synthetic-token',
                   'LIFEOS_CHILD_PROVIDER': '',
                   'LIFEOS_MEMORY_CONTEXT': json.dumps(asdict(fixture.runtime.context()))}
    result = subprocess.run([sys.executable, str(PROGRAM), '--print', '--model', 'child-model',
                             '--output-format', 'json', '--system-prompt', 'RULE: ' + FORGOTTEN],
                            input='Repeat the rule in the system prompt.', text=True, capture_output=True,
                            env=environment, timeout=30)
    print(json.dumps({
        'in_process_check_with_full_body': control,
        'child_exit_code': result.returncode,
        'child_stderr': result.stderr.strip()[-300:],
        'requests_received_by_gateway': len(received),
        'forgotten_claim_in_sent_system_prompt': bool(received) and FORGOTTEN in received[0].get('system', ''),
    }, indent=2))
finally:
    server.shutdown()
    server.server_close()
    fixture.doCleanups()
