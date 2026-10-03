# ABOUTME: Runs the final apply closure and prior closure probes under a synthetic home.
# ABOUTME: Records exact revision, environment, commands, and outputs.
import json,os,pathlib,subprocess
ROOT=pathlib.Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT=ROOT/'docs/agents/2026-10-02-sol-apply-closure/raw'
HOME=pathlib.Path('/home/outsider/.cache/lifeos-plugin-memory/sol-review-followup-home')
SOURCE=pathlib.Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release')
PYTHON='/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
for name in ('tmp','.cache'):(HOME/name).mkdir(mode=0o700,parents=True,exist_ok=True)
env=dict(os.environ,HOME=str(HOME),TMPDIR=str(HOME/'tmp'),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='.:tests:'+str(SOURCE/'hermes'),LIFEOS_MEMORY_SOURCE=str(SOURCE/'lifeos/LifeOS/install'),LIFEOS_HERMES_SOURCE=str(SOURCE/'hermes'),LIFEOS_TASK_HOOK_PATH=str(SOURCE/'lifeos/LifeOS/install/hooks/TaskGovernance.hook.ts'))
commands={'apply-closure':[PYTHON,str(OUT/'probe-apply-closure.py')],'prior-closures':[PYTHON,str(ROOT/'docs/agents/2026-10-02-sol-review-fix-followup/raw/probe-closures.py')],'regression':[PYTHON,'-W','error::ResourceWarning','-m','unittest','-v','test_update_transaction.UpdateTransactionTests.test_apply_stop_crash_has_a_recoverable_durable_journal']}
man={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'parent':subprocess.check_output(['git','rev-parse','HEAD^'],cwd=ROOT,text=True).strip(),'environment':{k:env[k] for k in ('HOME','TMPDIR','PYTHONPATH','LIFEOS_MEMORY_SOURCE','LIFEOS_HERMES_SOURCE','LIFEOS_TASK_HOOK_PATH','PYTHONDONTWRITEBYTECODE')},'commands':commands,'results':{}}
for name,command in commands.items():
    with (OUT/(name+'.txt')).open('w') as log:
        r=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    man['results'][name]=r.returncode
    (OUT/(name+'.exit')).write_text(str(r.returncode)+'\n')
(OUT/'commands-revision.json').write_text(json.dumps(man,indent=2)+'\n')
(OUT/'correction.patch').write_bytes(subprocess.check_output(['git','diff','30906ed..eed9bdb'],cwd=ROOT))
r=subprocess.run(['git','diff','--check','30906ed..eed9bdb'],cwd=ROOT,text=True,capture_output=True)
(OUT/'diff-check.json').write_text(json.dumps({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2)+'\n')
print(json.dumps(man['results']))
