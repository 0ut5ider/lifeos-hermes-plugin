# ABOUTME: Verifies native source admission and bounded collection with real memory fixtures.
# ABOUTME: Stores source identity, test output, and a completion marker for review.
import os
from pathlib import Path
import subprocess
import sys

OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]
SOURCE = Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-knowledge-relay-final')
environment = dict(os.environ, PYTHONPATH='.:tests',
    LIFEOS_MEMORY_SOURCE=str(SOURCE / 'lifeos/LifeOS/install'),
    LIFEOS_HERMES_SOURCE=str(SOURCE / 'hermes'),
    LIFEOS_PREPARE_HERMES_REPO='/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline',
    LIFEOS_PREPARE_LIFEOS_REPO='/home/outsider/.cache/lifeos-plugin-memory/managed-source')
command = [sys.executable, '-m', 'unittest', '-v', 'test_memory_wiki_corpus', 'test_memory_wiki_render',
    'test_memory_wiki_relay', 'test_memory_knowledge_relay', 'test_memory_knowledge_render',
    'test_memory_http', 'test_memory_sources', 'test_memory_canonical',
    'test_hermes_memory_provider', 'test_prepare_sources', 'test_patch_bundle']
(OUTPUT / 'gate.done').unlink(missing_ok=True)
with (OUTPUT / 'gate.txt').open('w') as log:
    log.write('Plugin commit: ' + subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() + '\n')
    log.write('Working diff:\n' + subprocess.check_output(['git', 'diff'], cwd=ROOT, text=True) + '\n')
    log.write('Source: ' + str(SOURCE) + '\n')
    log.write('Command: ' + ' '.join(command) + '\n')
    log.flush()
    result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
(OUTPUT / 'gate.done').write_text(str(result.returncode) + '\n')
sys.exit(result.returncode)
