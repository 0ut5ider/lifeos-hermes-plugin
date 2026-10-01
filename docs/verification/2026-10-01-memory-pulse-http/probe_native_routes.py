# ABOUTME: Measures native PULSE memory responses over real isolated localhost HTTP.
# ABOUTME: Uses synthetic profiles to distinguish request identity from process context.
from dataclasses import asdict
import json
import os
from pathlib import Path
import select
import subprocess
from urllib.request import urlopen
from test_memory_cortex_health import MemoryCortexHealthTests
from test_memory_native import SOURCE


def observe(label, *, ambient_owner=False, broken_connector=False):
    case = MemoryCortexHealthTests()
    case.setUp()
    server = None
    try:
        marker = 'Synthetic private PULSE network marker'
        saved = case.fixture.fixture.remember('RULE: ' + marker, 'pulse-network', 'principal')
        assert saved['status'] == 'committed', saved
        case.reviewer('Synthetic PULSE reviewer error marker')
        (case.obs / 'pending-proposals.jsonl').write_text(json.dumps({
            'id': 'synthetic-network-proposal', 'status': 'rejected', 'edit': marker}) + '\n')
        (case.obs / 'memory-health.jsonl').write_text(json.dumps({
            'ts': case.now, 'overall': 'warn', 'findings': [{'severity': 'warn', 'message': marker}]}) + '\n')
        if broken_connector:
            (case.root / 'LIFEOS/USER/CONFIG/memory-access.json').write_text('{invalid')
        environment = dict(os.environ, HOME=str(case.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL'):
            environment.pop(name, None)
        if ambient_owner:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(case.fixture.context))
        module = SOURCE / 'LIFEOS/PULSE/modules/memory.ts'
        code = ('const m=await import(' + json.dumps(str(module)) + '); '
                'const s=Bun.serve({hostname:"127.0.0.1",port:0,fetch:async(req)=>'
                '(await m.handleRequest(req,new URL(req.url).pathname))??new Response("missing",{status:404})});'
                'console.log(JSON.stringify({port:s.port}));')
        server = subprocess.Popen(['bun', '--no-install', '-e', code], cwd=case.root,
                                  env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready, _, _ = select.select([server.stdout], [], [], 10)
        assert ready, 'Synthetic PULSE HTTP server did not announce its port'
        port = json.loads(server.stdout.readline())['port']
        results = []
        for route in ('/api/memory', '/api/memory/state', '/api/memory/health', '/api/memory/runs'):
            with urlopen('http://127.0.0.1:' + str(port) + route, timeout=10) as response:
                body = response.read().decode()
                results.append({'route': route, 'status': response.status, 'body': json.loads(body),
                                'private_marker': marker in body})
        print(json.dumps({'case': label, 'ambient_owner': ambient_owner,
                          'broken_connector': broken_connector, 'requests_have_credentials': False,
                          'results': results}), flush=True)
    finally:
        if server is not None:
            server.terminate()
            stdout, stderr = server.communicate(timeout=5)
            assert stdout == '', stdout
            assert stderr == '', stderr
        case.doCleanups()


for label, owner, broken in [('missing-identity', False, False), ('ambient-owner', True, False),
                              ('broken-connector', True, True)]:
    observe(label, ambient_owner=owner, broken_connector=broken)
