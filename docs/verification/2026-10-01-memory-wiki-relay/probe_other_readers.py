# ABOUTME: Measures remaining native HTTP reader and writer boundaries on synthetic files.
# ABOUTME: Uses a real Bun listener without invoking sidecar remounts or model requests.
import json
import os
from pathlib import Path
import select
import shutil
import subprocess

import httpx

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER, SOURCE
from lifeos_hook_bridge.memory_access import MemoryConflict
from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError, MemoryRuntime

OUTPUT = Path(__file__).resolve().parent
fixture = delegation_fixture.MemoryDelegationTests()
fixture.setUp()
process = None
results = {}
try:
    root, memory = fixture.root, fixture.fixture.memory
    environment = dict(os.environ, HOME=str(fixture.fixture.home),
        HERMES_HOME=str(fixture.fixture.home / 'hermes'), BUN_CONFIG_NO_AUTO_INSTALL='1')
    environment.pop('LIFEOS_MEMORY_INTERNAL', None)
    environment.pop('LIFEOS_MEMORY_CONTEXT', None)
    (root / 'LIFEOS/PULSE').symlink_to(SOURCE / 'LIFEOS/PULSE')
    shutil.copytree(SOURCE / 'LIFEOS/HERMES', root / 'LIFEOS/HERMES')
    for relative, content in {
        'LIFEOS/LIFEOS_SYSTEM_PROMPT.md': '# Synthetic constitution\nSynthetic verification rules.\n',
        'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md': '**Name:** SyntheticReaderDA\n## Personality\nSyntheticOtherReaderIdentityClaim\n',
        'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md': '## Quick Reference\nSynthetic principal identity.\n',
        'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md': '## Missions\nSynthetic mission.\n',
        'LIFEOS/USER/PROJECTS.md': '| **SyntheticReaderProject** | active |\n',
    }.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    saved = fixture.fixture.remember('SyntheticOtherReaderForgottenMarker', 'other-reader-current')
    assert saved['status'] == 'committed', saved
    hot = fixture.fixture.remember('RULE: SyntheticOtherReaderHotMarker', 'other-reader-hot', 'principal')
    assert hot['status'] == 'committed', hot
    identity = fixture.fixture.remember('RULE: SyntheticOtherReaderIdentityClaim', 'other-reader-identity', 'principal')
    assert identity['status'] == 'committed', identity
    assert memory.forget(OWNER, identity['reference'], 'other-reader-forget-identity')['status'] == 'committed'
    rendered = subprocess.run(['bun', '--no-install', str(root / 'LIFEOS/HERMES/RenderSoul.ts')],
        env=environment, capture_output=True, text=True, timeout=20)
    assert rendered.returncode == 0 and not rendered.stderr, rendered.stderr
    results['native_mount_renderer'] = {'status': rendered.returncode, 'caller_context': False,
        'contains_forgotten_identity_claim': 'SyntheticOtherReaderIdentityClaim' in rendered.stdout,
        'contains_current_hot_claim': 'SyntheticOtherReaderHotMarker' in rendered.stdout}
    (fixture.configuration.path.parent / 'SOUL.md').write_text(rendered.stdout)
    with memory._transaction() as connection:
        try:
            MemoryRuntime(fixture.configuration.path)._rendered_prompt(fixture.configuration.load(), OWNER, connection)
            results['generated_prompt_guard'] = {'refused': False}
        except MemoryAdmissionError as error:
            results['generated_prompt_guard'] = {'refused': True, 'reason': str(error)}
    note = next((root / 'LIFEOS/MEMORY/KNOWLEDGE/Research').glob('*.md'))
    unknown = note.with_name('synthetic-other-reader-unknown.md')
    unknown.write_text('---\nid: synthetic-other-reader-unknown\ntitle: SyntheticOtherReaderUnknownTitle\n'
                       'type: research\ncreated: 2026-10-01\nupdated: 2026-10-01\n---\nSyntheticOtherReaderUnknownBody\n')
    graph = root / 'LIFEOS/MEMORY/GRAPH/graph.json'
    graph.parent.mkdir()
    graph.write_text(json.dumps({'generated': '2026-10-01T00:00:00Z', 'nodeCount': 1, 'edgeCount': 0,
        'nodes': [{'id': 'synthetic-forgotten-node', 'silo': 'knowledge', 'type': 'research',
            'title': 'SyntheticOtherReaderForgottenMarker', 'community': 1, 'pagerank': 1, 'degree': 0, 'tags': []}],
        'edges': []}))
    program = fixture.fixture.home / 'remaining-readers.ts'
    program.write_text('import {startObservability,handleObservabilityRequest} from '
        + json.dumps(str(root / 'LIFEOS/PULSE/Observability/observability.ts'))
        + ';import {handleRequest} from ' + json.dumps(str(root / 'LIFEOS/PULSE/modules/hermes.ts'))
        + ';startObservability({enabled:true});'
        + 'const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){'
        + 'const path=new URL(request.url).pathname;return await(path.startsWith("/api/hermes")?'
        + 'handleRequest(request,path):handleObservabilityRequest(request))??new Response("not found",{status:404});}});'
        + 'console.log(server.port);')
    process = subprocess.Popen(['bun', '--no-install', str(program)], env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert select.select([process.stdout], [], [], 15)[0], 'The native reader listener did not start'
    first = process.stdout.readline().strip()
    assert first.isdigit(), first
    base = 'http://127.0.0.1:' + first

    def fetch(label, path, *, method='GET', content=None):
        response = httpx.request(method, base + path, json={'content': content} if content is not None else None,
                                 timeout=20)
        results[label] = {'method': method, 'path': path, 'status': response.status_code,
            'cache_control': response.headers.get('cache-control'), 'body': response.json()}

    fetch('anonymous_knowledge_index', '/api/knowledge')
    fetch('anonymous_current_knowledge_body', '/api/knowledge/research/' + note.stem)
    results['forget_receipt'] = memory.forget(OWNER, saved['reference'], 'other-reader-forget')
    fetch('anonymous_forgotten_knowledge_body', '/api/knowledge/research/' + note.stem)
    fetch('direct_observability_forgotten_graph', '/api/memory/graph')
    fetch('anonymous_native_sidecar_hot_body', '/api/hermes/file/principal-memory')
    fetch('unreviewed_native_knowledge_write', '/api/knowledge/research/' + note.stem,
          method='PUT', content='---\ntitle: SyntheticOtherReaderEditedTitle\n---\nSyntheticOtherReaderUnreviewedBody\n')
    results['knowledge_written_bytes'] = note.read_text()
    fetch('unreviewed_native_sidecar_hot_write', '/api/hermes/file/principal-memory', method='PUT',
          content='---\nlast_updated_by: synthetic\n---\n<!-- BEGIN ENTRIES -->\nRULE: SyntheticOtherReaderUntrackedHot\n<!-- END ENTRIES -->\n')
    try:
        results['hot_reference_after_raw_write'] = memory.get(OWNER, hot['reference'])
    except MemoryConflict as error:
        results['hot_reference_after_raw_write'] = {'status': 'conflict', 'reason': str(error)}
    results['backup_count'] = len(list((root / 'LIFEOS/MEMORY/STATE/hermes-edits').glob('*')))
finally:
    if process is not None:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
        (OUTPUT / 'other-reader-process.txt').write_text(stdout + stderr)
    fixture.doCleanups()
    (OUTPUT / 'other-readers-before.json').write_text(json.dumps(results, indent=2) + '\n')
