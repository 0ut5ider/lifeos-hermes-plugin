# ABOUTME: Measures anonymous delivery through actual selected native Pulse module listeners.
# ABOUTME: Uses disposable managed owner files and records responses without external model requests.
import json
import os
from pathlib import Path
import select
import subprocess
import sys

import httpx
import test_memory_pulse_auth as auth_fixture

fixture = auth_fixture.MemoryPulseAuthTests()
fixture.setUp()
root = fixture.fixture.fixture.fixture.fixture.root
source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
records = []
process = None
try:
    marker = root / 'LIFEOS/USER/CONFIG/memory-http.json'
    marker.write_text('{"version":1,"managed":true}')
    marker.chmod(0o600)
    files = {
        'USER/BOOKS.md': '# Books\n## Synthetic books\n- title: "<private>SyntheticModulePrivateBook</private>"\n  author: "Synthetic Author"\n',
        'USER/PROJECTS.md': '| Project | Path | URL | Deploy | Stack |\n| --- | --- | --- | --- | --- |\n| SyntheticModulePrivateProject | /synthetic | https://example.invalid | local | Python |\n',
        'USER/PROJECTS_RETIRED.md': '',
        'USER/TELOS/TELOS.md': '',
        'USER/GEAR.md': '## Devices\n| **Laptop** | SyntheticModulePrivateDevice | Work |\n',
        'USER/SECURITY/THREATMODEL/risk-register.json': '{}',
        'MEMORY/STATE/Evals-Results/SyntheticModulePrivateSuite/latest.json': '{}',
    }
    for relative, content in files.items():
        path = root / 'LIFEOS' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    modules = {'books': 'books.ts', 'projects': 'projects.ts', 'assets': 'assets.ts',
               'threatmodel': 'threatmodel.ts', 'evals': 'evals.ts'}
    program = fixture.home / 'selected-module-audit.ts'
    imports = '\n'.join('import * as ' + key + ' from ' + json.dumps(str(
        source / 'LIFEOS/PULSE/modules' / name)) + ';' for key, name in modules.items())
    program.write_text(imports + '\nconst modules={' + ','.join(modules) + '};\n'
        'const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(req){\n'
        'const path=new URL(req.url).pathname;for(const [name,module] of Object.entries(modules)){\n'
        'if(path.startsWith("/api/"+name))return await module.handleRequest(req,path)??new Response("not found",{status:404});}\n'
        'return new Response("not found",{status:404});}});console.log(server.port);\n')
    environment = dict(os.environ, HOME=str(fixture.home), CLAUDE_CONFIG_DIR=str(root), LIFEOS_DIR=str(root / 'LIFEOS'),
        THREATMODEL_DATA_DIR=str(root / 'LIFEOS/USER/SECURITY/THREATMODEL'), BUN_CONFIG_NO_AUTO_INSTALL='1',
        LIFEOS_MEMORY_INTERNAL='1', LIFEOS_MEMORY_CONTEXT='{"principal":"owner","author":"100"}')
    process = subprocess.Popen(['bun', '--no-install', str(program)], env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if not select.select([process.stdout], [], [], 10)[0]: raise RuntimeError('Native audit listener did not start')
    base = 'http://127.0.0.1:' + process.stdout.readline().strip()
    for route in ('/api/books', '/api/books/status', '/api/projects', '/api/projects/status',
                  '/api/assets', '/api/assets/status', '/api/threatmodel', '/api/evals'):
        response = httpx.get(base + route, headers={'X-LifeOS-Owner': 'owner'}, timeout=10)
        records.append({'route': route, 'status': response.status_code,
            'cache_control': response.headers.get('cache-control'), 'synthetic_private_label': 'SyntheticModulePrivate' in response.text,
            'body': response.json()})
finally:
    if process:
        process.terminate()
        output, errors = process.communicate(timeout=10)
        if output or errors: records.append({'native_output': output, 'native_errors': errors})
    fixture.doCleanups()
print(json.dumps({'scope': 'selected public native modules, synthetic managed home, anonymous HTTP',
    'observations': records}, indent=2))
