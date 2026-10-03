# ABOUTME: Measures native wiki request admission and retained index behavior on localhost.
# ABOUTME: Uses disposable native sources and captures actual route responses without a model.
from dataclasses import asdict
import json
import os
from pathlib import Path
import select
import subprocess

import httpx
import test_memory_delegation as delegation_fixture
from test_memory_native import SOURCE, OWNER

fixture = delegation_fixture.MemoryDelegationTests()
fixture.setUp()
output = Path(__file__).resolve().parent
responses = {}
process = None
try:
    root = fixture.root
    (root / 'LIFEOS/PULSE').symlink_to(SOURCE / 'LIFEOS/PULSE')
    native = fixture.fixture.memory
    saved = fixture.fixture.remember('SyntheticWikiCurrentFactMarker', 'wiki-current')
    note = next((root / 'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    slug = note.stem
    unknown = note.with_name('synthetic-unknown-wiki.md')
    unknown.write_text('---\nid: synthetic-wiki-unknown\ntitle: SyntheticWikiUnregisteredMarker\n'
                      'type: research\n---\nSyntheticWikiUnregisteredMarker\n')
    program = fixture.fixture.home / 'wiki-probe.ts'
    program.write_text('import {startWiki,handleWikiRequest,stopWiki} from '
        + json.dumps(str(root / 'LIFEOS/PULSE/modules/wiki.ts')) + ';\n'
        'startWiki();\n'
        'const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){\n'
        'return await handleWikiRequest(request,new URL(request.url).pathname) ?? new Response("not found",{status:404});}});\n'
        'console.log("WIKI_PORT="+server.port);\n'
        'process.on("SIGTERM",()=>{stopWiki();server.stop(true);process.exit(0)});\n')
    environment = dict(os.environ, HOME=str(fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1',
                       LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(fixture.context)))
    environment.pop('LIFEOS_MEMORY_INTERNAL', None)
    process = subprocess.Popen(['bun', '--no-install', str(program)], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert select.select([process.stdout], [], [], 15)[0], 'The real wiki listener did not start'
    first = process.stdout.readline().strip()
    assert first.startswith('WIKI_PORT='), first
    base = 'http://127.0.0.1:' + first.split('=', 1)[1]

    def fetch(label, path):
        response = httpx.get(base + path, timeout=20)
        responses[label] = {'path': path, 'status': response.status_code,
                            'cache_control': response.headers.get('cache-control'), 'body': response.json()}

    fetch('anonymous_index', '/api/wiki')
    fetch('anonymous_unknown_note', '/api/wiki/knowledge/research/' + unknown.stem)
    fetch('anonymous_current_note', '/api/wiki/knowledge/research/' + slug)
    fetch('anonymous_search', '/api/wiki/search?q=SyntheticWikiUnregisteredMarker')
    fetch('anonymous_graph', '/api/wiki/graph')
    responses['forget_receipt'] = native.forget(OWNER, saved['reference'], 'wiki-forget')
    fetch('after_forget_index', '/api/wiki')
    fetch('after_forget_note', '/api/wiki/knowledge/research/' + slug)
    fetch('after_forget_graph', '/api/wiki/graph')
finally:
    if process is not None:
        process.terminate()
        stdout, stderr = process.communicate(timeout=15)
        (output / 'native-process.txt').write_text(stdout + stderr)
        responses['process_exit'] = process.returncode
    (output / 'before.json').write_text(json.dumps(responses, indent=2) + '\n')
    fixture.doCleanups()
