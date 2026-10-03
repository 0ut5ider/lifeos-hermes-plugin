# ABOUTME: Exercises direct child ownership and revocation using a local endpoint.
# ABOUTME: Captures child requests with synthetic configuration and memory only.
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess
import sys
import threading
from test_memory_runtime import MemoryRuntimeTests
from test_memory_children import PROGRAM
from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_service import MemoryConfiguration
fixture = MemoryRuntimeTests()
fixture.setUp()
received = []
class Gateway(BaseHTTPRequestHandler):
    def do_POST(self):
        received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        body = b'{"type":"message","content":[{"type":"text","text":"Synthetic OK"}]}'
        self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *_): pass
server = ThreadingHTTPServer(('127.0.0.1',0),Gateway)
thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
try:
    base_url = f'http://127.0.0.1:{server.server_port}'
    route = route_identity(provider='lifeos-local-gateway',model='child-model',base_url=base_url,api_mode='anthropic')
    fixture.configuration['destinations']['chat-a:200']['model_routes'].append(route)
    MemoryConfiguration(fixture.path).save(fixture.configuration)
    fixture.admit(session='synthetic-child-review')
    environment = {**os.environ, 'HOME':str(fixture.fixture.home),'HERMES_HOME':str(fixture.home),
                   'ANTHROPIC_BASE_URL':base_url,'ANTHROPIC_AUTH_TOKEN':'synthetic-token','LIFEOS_CHILD_PROVIDER':'',
                   'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(fixture.runtime.context()))}
    command = [sys.executable,str(PROGRAM),'--print','--model','child-model','--output-format','json','--system-prompt','Synthetic current prompt']
    def run(case):
        count = len(received)
        result = subprocess.run(command,input='Synthetic generated content',text=True,capture_output=True,env=environment,timeout=10)
        output = {'case':case,'exit':result.returncode,'gateway_requests':len(received)-count,'stderr':result.stderr,'stdout':result.stdout}
        print(json.dumps(output,sort_keys=True))
        return result.returncode, len(received)-count
    assert run('approved') == (0,1)
    MemoryConfiguration(fixture.path).update(lambda c:c['destinations']['chat-a:200']['model_routes'].remove(route))
    exit_code,count = run('route_revoked'); assert exit_code and count == 0
    MemoryConfiguration(fixture.path).update(lambda c:c.update(ownership_enabled=False))
    exit_code,count = run('disabled_retained_context'); assert exit_code and count == 0
    environment.pop('LIFEOS_MEMORY_CONTEXT')
    environment.pop('LIFEOS_MEMORY_SESSION',None)
    assert run('disabled_fresh_child') == (0,1)
finally:
    server.shutdown(); server.server_close(); thread.join()
    fixture.doCleanups()
