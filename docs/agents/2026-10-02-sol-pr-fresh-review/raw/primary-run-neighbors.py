# ABOUTME: Reruns native source neighbors with the declared public governance hook.
# ABOUTME: Records the command, native fixture environment, and completion status.
import os,pathlib,shutil,subprocess,json
ROOT=pathlib.Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin');OUT=ROOT/'docs/agents/2026-10-02-sol-pr-fresh-review/raw';HOME=OUT/'primary-neighbors-home';SOURCE=pathlib.Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release')
for d in ('tmp','.cache','.bun/bin'):(HOME/d).mkdir(parents=True,exist_ok=True,mode=0o700)
if not (HOME/'.bun/bin/bun').exists():(HOME/'.bun/bin/bun').symlink_to(shutil.which('bun'))
env=dict(os.environ,HOME=str(HOME),TMPDIR=str(HOME/'tmp'),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='.:tests:'+str(SOURCE/'hermes'),LIFEOS_MEMORY_SOURCE=str(SOURCE/'lifeos/LifeOS/install'),LIFEOS_HERMES_SOURCE=str(SOURCE/'hermes'),LIFEOS_TASK_HOOK_PATH=str(SOURCE/'lifeos/LifeOS/install/hooks/TaskGovernance.hook.ts'))
cmd=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python','-W','error::ResourceWarning','-m','unittest','-v','test_update_transaction.UpdateTransactionTests.test_capability_record_applies_and_restores_with_native_hook_files','test_memory_adoption','test_memory_canonical','test_memory_staging','test_memory_knowledge_render']
with (OUT/'primary-native-neighbors.txt').open('w') as log:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
(OUT/'primary-native-neighbors.json').write_text(json.dumps({'command':cmd,'environment':{k:env[k] for k in ('HOME','TMPDIR','PYTHONPATH','LIFEOS_MEMORY_SOURCE','LIFEOS_HERMES_SOURCE','LIFEOS_TASK_HOOK_PATH')},'exit':r.returncode},indent=2)+'\n');(OUT/'primary-native-neighbors.done').touch()
