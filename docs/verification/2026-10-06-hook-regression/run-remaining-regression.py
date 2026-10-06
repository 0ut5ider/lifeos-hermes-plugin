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
env['TMPDIR']='/home/outsider/.cache/lhc6'
commands=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python','-m','unittest','-v','test_profile_backup.ProfileBackupScopeTests.test_regenerable_and_runtime_entries_are_excluded_and_recorded','test_ownership_setup.OwnershipSetupTests.test_originally_inactive_service_stays_inactive_after_setup_and_return','test_ownership_setup_host.OwnershipSetupHostTests.test_restarted_profile_uses_native_tools_and_returns_to_preserved_hermes_memory']
with (cache/'remaining-regression.txt').open('w') as stream:
 result=subprocess.run(commands,cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT)
(cache/'remaining-regression.done').write_text(str(result.returncode)+'\n')
