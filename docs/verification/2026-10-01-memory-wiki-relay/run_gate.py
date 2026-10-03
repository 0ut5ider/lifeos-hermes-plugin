# ABOUTME: Runs distributed wiki, relay, authentication, and source preparation gates.
# ABOUTME: Writes exact test output and a completion marker that survives session loss.
import os
from pathlib import Path
import subprocess
import sys

OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]
SOURCE = Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-wiki-relay-final')
PYTHON = '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
environment = dict(os.environ, PYTHONPATH='.:tests',
    LIFEOS_MEMORY_SOURCE=str(SOURCE / 'lifeos/LifeOS/install'), LIFEOS_HERMES_SOURCE=str(SOURCE / 'hermes'),
    LIFEOS_PREPARE_HERMES_REPO='/home/outsider/Projects/Hermes_agent/upstream/final-gate-baseline',
    LIFEOS_PREPARE_LIFEOS_REPO='/home/outsider/.cache/lifeos-plugin-memory/managed-source')
label = sys.argv[1]
if label == 'focused':
    modules = ['test_memory_wiki_relay', 'test_memory_wiki_render', 'test_memory_pulse_relay',
        'test_memory_pulse_auth', 'test_memory_http', 'test_memory_canonical', 'test_prepare_sources', 'test_patch_bundle']
elif label == 'regression':
    modules = [path.stem for path in sorted((ROOT / 'tests').glob('test_memory*.py'))]
else:
    raise ValueError('Choose focused or regression')
(OUTPUT / (label + '.done')).unlink(missing_ok=True)
with (OUTPUT / (label + '.txt')).open('w') as log:
    log.write('Prepared source: ' + str(SOURCE) + '\n')
    log.write('Plugin commit: ' + subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() + '\n')
    log.write('Command: ' + ' '.join([PYTHON, '-m', 'unittest', '-v', *modules]) + '\n')
    log.flush()
    result = subprocess.run([PYTHON, '-m', 'unittest', '-v', *modules], cwd=ROOT, env=environment,
                            stdout=log, stderr=subprocess.STDOUT)
    status = result.returncode
    if label == 'regression':
        command = [PYTHON, '-m', 'unittest', '-v', 'test_hermes_memory_provider', 'test_prepare_sources', 'test_patch_bundle']
        log.write('Command: ' + ' '.join(command) + '\n')
        log.flush()
        neighbors = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        if neighbors.returncode:
            status = neighbors.returncode
(OUTPUT / (label + '.done')).write_text(str(status) + '\n')
sys.exit(status)
