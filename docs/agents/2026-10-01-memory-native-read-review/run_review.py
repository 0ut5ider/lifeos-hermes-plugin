# ABOUTME: Runs focused memory read tests in disposable local fixtures.
# ABOUTME: Stores test output and completion status for independent review.
import os
from pathlib import Path
import subprocess
import sys
root = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
out = Path(__file__).resolve().parent / 'raw'
source = Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-knowledge-relay-final')
env = dict(os.environ, PYTHONPATH='.:tests', LIFEOS_MEMORY_SOURCE=str(source / 'lifeos/LifeOS/install'), LIFEOS_HERMES_SOURCE=str(source / 'hermes'), LIFEOS_PREPARE_HERMES_REPO='/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline', LIFEOS_PREPARE_LIFEOS_REPO='/home/outsider/.cache/lifeos-plugin-memory/managed-source')
command = [sys.executable, '-m', 'unittest', '-v', 'test_memory_wiki_corpus', 'test_memory_wiki_render', 'test_memory_wiki_relay', 'test_memory_knowledge_relay', 'test_memory_knowledge_render', 'test_memory_http', 'test_memory_sources', 'test_memory_canonical']
with (out / 'focused-tests.txt').open('w') as log:
    log.write('Command: ' + ' '.join(command) + '\n')
    log.flush()
    result = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
(out / 'focused-tests.done').write_text(str(result.returncode) + '\n')
