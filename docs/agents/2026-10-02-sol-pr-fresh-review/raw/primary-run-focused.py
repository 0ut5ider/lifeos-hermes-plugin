# ABOUTME: Independently reruns the fresh review selections in a separate synthetic home.
# ABOUTME: Saves exact commands, outputs, and exits without contacting live services.
import json, os, pathlib, shutil, subprocess
ROOT=pathlib.Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT=ROOT/'docs/agents/2026-10-02-sol-pr-fresh-review/raw'
HOME=OUT/'primary-fixture-home'
for directory in ('tmp','.cache','.bun/bin'):(HOME/directory).mkdir(parents=True,exist_ok=True,mode=0o700)
(HOME/'.bun/bin/bun').symlink_to(shutil.which('bun')) if not (HOME/'.bun/bin/bun').exists() else None
SOURCE=pathlib.Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release')
env=dict(os.environ,HOME=str(HOME),TMPDIR=str(HOME/'tmp'),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='.:tests:'+str(SOURCE/'hermes'),LIFEOS_MEMORY_SOURCE=str(SOURCE/'lifeos/LifeOS/install'),LIFEOS_HERMES_SOURCE=str(SOURCE/'hermes'))
commands={'transactions': ['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python', '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', 'test_installation_lock', 'test_update_transaction', 'test_update_worker', 'test_mount_transaction', 'test_memory_admin_dashboard', 'test_memory_administration', 'test_memory_prompt', 'test_memory_source_review'], 'memory-boundaries': ['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python', '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', 'test_hermes_memory_provider', 'test_memory_service', 'test_memory_native', 'test_memory_model_calls', 'test_memory_runtime', 'test_memory_history', 'test_memory_authorization', 'test_memory_context', 'test_memory_knowledge_query', 'test_memory_wiki_corpus'], 'recorder': ['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python', '-W', 'error::ResourceWarning', '-m', 'unittest', 'discover', '-v', '-s', 'development/tests'], 'dashboard': ['node', '--test', 'tests/test_dashboard_ui.cjs', 'tests/test_memory_dashboard_ui.cjs'], 'source-neighbors': ['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python', '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', 'test_memory_adoption', 'test_memory_canonical', 'test_memory_knowledge_render', 'test_memory_staging', 'test_update_transaction']}
result={'commands':commands,'results':{},'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
for name,cmd in commands.items():
    with (OUT/('primary-'+name+'.txt')).open('w') as log:
        process=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    result['results'][name]=process.returncode
    (OUT/'primary-test-results.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'primary.done').touch()
