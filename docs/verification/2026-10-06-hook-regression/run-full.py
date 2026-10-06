import os,subprocess
from pathlib import Path
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
cache=Path('/home/outsider/.cache/lifeos-hook-completion-20261006')
source=cache/'prepared-final'
lifeos=source/'lifeos/LifeOS/install'
env={**os.environ,'TMPDIR':str(cache/'gate-tmp'),'PYTHONPATH':'tests:.'+':'+str(source/'hermes'),
'LIFEOS_HERMES_SOURCE':str(source/'hermes'),'LIFEOS_MEMORY_SOURCE':str(lifeos),'LIFEOS_FRESH_SOURCE':str(source/'lifeos'),
'LIFEOS_FRESH_EVIDENCE':str(cache/'fresh-evidence'),'LIFEOS_TASK_HOOK_PATH':str(lifeos/'hooks/TaskGovernance.hook.ts'),
'LIFEOS_PREPARE_HERMES_REPO':'/home/outsider/.cache/lifeos-footprint-20260929/hermes-clean',
'LIFEOS_PREPARE_LIFEOS_REPO':'/home/outsider/.cache/lifeos-footprint-20260929/lifeos-clean',
'LIFEOS_FRESHNESS_CONTROL_SOURCE':'/home/outsider/.cache/lifeos-full-experience-20261004/lifecycle/memory-telos-final-distributed/lifeos/LifeOS/install',
'LIFEOS_PULSE_SOURCE':str(lifeos),'LIFEOS_TAB_STATE_SOURCE':str(lifeos),'LIFEOS_CONFIG_AUDIT_SOURCE':str(lifeos),
'LIFEOS_AGENT_INVOCATION_PATH':str(lifeos/'hooks/AgentInvocation.hook.ts')}
commands=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python','-m','unittest',*[p.stem for p in sorted((repo/'tests').glob('test_*.py'))]]
with (cache/'full-final.txt').open('w') as output:
 result=subprocess.run(commands,cwd=repo,env=env,stdout=output,stderr=subprocess.STDOUT)
(cache/'full-final.done').write_text(str(result.returncode)+'\n')
