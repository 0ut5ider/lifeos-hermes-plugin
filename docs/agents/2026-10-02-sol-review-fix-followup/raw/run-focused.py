# ABOUTME: Verifies bounded restore and source-label corrections with public sources.
# ABOUTME: Records commands and results under a separate synthetic home.
import json, os, pathlib, shutil, subprocess
ROOT=pathlib.Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT=ROOT/'docs/agents/2026-10-02-sol-review-fix-followup/raw'
HOME=pathlib.Path('/home/outsider/.cache/lifeos-plugin-memory/sol-review-followup-home')
HOME.mkdir(mode=0o700,exist_ok=True)
for name in ('tmp','.cache','.bun/bin'):
    (HOME/name).mkdir(mode=0o700,parents=True,exist_ok=True)
if not (HOME/'.bun/bin/bun').exists():
    (HOME/'.bun/bin/bun').symlink_to(shutil.which('bun'))
SOURCE=pathlib.Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release')
PYTHON='/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
env=dict(os.environ,HOME=str(HOME),TMPDIR=str(HOME/'tmp'),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='.:tests:'+str(SOURCE/'hermes'),LIFEOS_MEMORY_SOURCE=str(SOURCE/'lifeos/LifeOS/install'),LIFEOS_HERMES_SOURCE=str(SOURCE/'hermes'),LIFEOS_TASK_HOOK_PATH=str(SOURCE/'lifeos/LifeOS/install/hooks/TaskGovernance.hook.ts'))
commands={'focused':[PYTHON,'-W','error::ResourceWarning','-m','unittest','-v','test_update_transaction','test_update_worker','test_memory_admin_dashboard','test_memory_source_labels','test_memory_canonical'],'dashboard':['node','--test','tests/test_dashboard_ui.cjs','tests/test_memory_dashboard_ui.cjs']}
manifest={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'review_base':subprocess.check_output(['git','rev-parse','85c0902'],cwd=ROOT,text=True).strip(),'environment':{k:env[k] for k in ('HOME','TMPDIR','PYTHONPATH','LIFEOS_MEMORY_SOURCE','LIFEOS_HERMES_SOURCE','LIFEOS_TASK_HOOK_PATH','PYTHONDONTWRITEBYTECODE')},'commands':commands,'results':{}}
(OUT/'commands-revision.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name,command in commands.items():
    with (OUT/(name+'.txt')).open('w') as log:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    manifest['results'][name]=result.returncode
    (OUT/(name+'.exit')).write_text(str(result.returncode)+'\n')
    (OUT/'commands-revision.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'.done').touch()
