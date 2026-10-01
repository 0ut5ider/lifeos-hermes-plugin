# ABOUTME: Runs closure tests and independent probes in disposable native fixtures.
# ABOUTME: Preserves commands, source hashes, outputs, and a completion marker on disk.
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'raw'
SOURCE = Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-knowledge-relay-final')
environment = dict(os.environ, PYTHONPATH='.:tests',
    LIFEOS_MEMORY_SOURCE=str(SOURCE / 'lifeos/LifeOS/install'),
    LIFEOS_HERMES_SOURCE=str(SOURCE / 'hermes'))
files = ['lifeos_hook_bridge/memory_sources.py', 'lifeos_hook_bridge/memory_wiki.py',
         'tests/test_memory_wiki_corpus.py', 'lifeos_hook_bridge/memory_native.ts']
manifest = {}
for filename in files:
    content = (ROOT / filename).read_bytes()
    destination = OUT / 'sources' / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    manifest[filename] = hashlib.sha256(content).hexdigest()
(OUT / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
(OUT / 'reviewed.diff').write_bytes(subprocess.check_output(['git', 'diff', '--', *files], cwd=ROOT))
commands = [
    [sys.executable, '-m', 'unittest', '-v', 'test_memory_wiki_corpus', 'test_memory_wiki_render',
     'test_memory_sources', 'test_memory_canonical'],
    [sys.executable, str(HERE / 'probe_closure.py')],
]
codes = []
for name, command in zip(('focused-tests', 'probes'), commands, strict=True):
    with (OUT / (name + '.txt')).open('w') as log:
        log.write('Command: ' + ' '.join(command) + '\n')
        log.flush()
        completed = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    codes.append(completed.returncode)
    (OUT / (name + '.done')).write_text(str(completed.returncode) + '\n')
(OUT / 'closure.done').write_text(json.dumps(codes) + '\n')
sys.exit(int(any(codes)))
