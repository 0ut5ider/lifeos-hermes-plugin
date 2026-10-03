# ABOUTME: Runs bounded review tests against public sources and a private synthetic home.
# ABOUTME: Records commands and exits without reaching services or private data.
import json, os, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT = ROOT / 'docs/agents/2026-10-02-sol-pr-fresh-review/raw'
HOME = OUT / 'fixture-home'
for name in ('tmp', '.cache', '.bun/bin'):
    (HOME / name).mkdir(parents=True, exist_ok=True, mode=0o700)
if not (HOME / '.bun/bin/bun').exists():
    (HOME / '.bun/bin/bun').symlink_to(shutil.which('bun'))
SOURCE = pathlib.Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release')
PYTHON = '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
env = dict(os.environ, HOME=str(HOME), TMPDIR=str(HOME/'tmp'), PYTHONDONTWRITEBYTECODE='1',
    PYTHONPATH='.:tests:' + str(SOURCE/'hermes'), LIFEOS_MEMORY_SOURCE=str(SOURCE/'lifeos/LifeOS/install'),
    LIFEOS_HERMES_SOURCE=str(SOURCE/'hermes'))
commands = {
    'transactions': [PYTHON, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', 'test_installation_lock', 'test_update_transaction', 'test_update_worker', 'test_mount_transaction', 'test_memory_admin_dashboard', 'test_memory_administration', 'test_memory_prompt', 'test_memory_source_review'],
    'memory-boundaries': [PYTHON, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', 'test_hermes_memory_provider', 'test_memory_service', 'test_memory_native', 'test_memory_model_calls', 'test_memory_runtime', 'test_memory_history', 'test_memory_authorization', 'test_memory_context', 'test_memory_knowledge_query', 'test_memory_wiki_corpus'],
    'recorder': [PYTHON, '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover', '-v', '-s', 'development/tests'],
    'dashboard': ['node', '--test', 'tests/test_dashboard_ui.cjs', 'tests/test_memory_dashboard_ui.cjs'],
}
manifest = {'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'base':subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip(),
    'environment':{k:env[k] for k in ('HOME','TMPDIR','PYTHONPATH','LIFEOS_MEMORY_SOURCE','LIFEOS_HERMES_SOURCE')},
    'sources':json.loads((SOURCE/'source-manifest.json').read_text()),'commands':commands,'results':{}}
(OUT/'commands-revision.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name,cmd in commands.items():
    with (OUT/(name+'.txt')).open('w') as log:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    manifest['results'][name] = result.returncode
    (OUT/(name+'.exit')).write_text(str(result.returncode)+'\n')
    (OUT/'commands-revision.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'.done').touch()
