# ABOUTME: Runs the complete current test inventory in four isolated regression suites.
# ABOUTME: Retains commands, source bindings, signal state, results, and completion markers.
from pathlib import Path
import concurrent.futures
import json
import os
import signal
import subprocess
import time

cache=Path('/home/outsider/.cache/lifeos-step1-20261007/full-review-final')
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
target=Path('/home/outsider/.cache/lifeos-step1-20261007/installer-review-final')
source=Path('/home/outsider/.cache/lifeos-step1-20261007/prepared-review-final')
lifeos=source/'lifeos/LifeOS/install'
env={**os.environ,'TMPDIR':'/home/outsider/.cache/lhc6','PYTHONPATH':'tests:.'+':'+str(source/'hermes'),
'LIFEOS_HERMES_SOURCE':str(source/'hermes'),'LIFEOS_HERMES_REBUILD_SOURCE':str(source/'hermes'),
'LIFEOS_MEMORY_SOURCE':str(lifeos),'LIFEOS_FRESH_SOURCE':str(target),
'LIFEOS_PREPARE_HERMES_REPO':'/home/outsider/.cache/lifeos-footprint-20260929/hermes-clean',
'LIFEOS_PREPARE_LIFEOS_REPO':'/home/outsider/.cache/lifeos-footprint-20260929/lifeos-clean',
'LIFEOS_RTK_BINARY':'/home/outsider/.cache/lifeos-step1-20261006/rtk',
'HERMES_POLICY_SOURCE':str(source/'hermes'),'LIFEOS_PERMISSION_HOOK':str(lifeos/'hooks/Safety.hook.ts')}
for key in ['PULSE','TAB_STATE','CONFIG_AUDIT','GUARD','RTK']:
 env['LIFEOS_'+key+'_SOURCE']=str(lifeos)
env['LIFEOS_FRESHNESS_CONTROL_SOURCE']='/home/outsider/.cache/lifeos-full-experience-20261004/lifecycle/memory-telos-final-distributed/lifeos/LifeOS/install'
for key,name in {
 'TASK_HOOK':'TaskGovernance','AGENT_INVOCATION':'AgentInvocation','CHECKPOINT_HOOK':'CheckpointPerISC',
 'DRIFT_REMINDER':'DriftReminder','HOOK_HEALER':'HookHealer','MODEL_RUNG_GUARD':'ModelRungGuard',
 'PROMPT_PROCESSING':'PromptProcessing','VERSION_DRIFT':'VersionDrift','LOOP_DETECTOR':'LoopDetector',
 'EVENT_LOGGER_HOOK':'EventLogger','WORK_COMPLETION':'WorkCompletionLearning','SESSION_CLEANUP':'SessionCleanup',
 'VOICE_HOOK':'VoiceCompletion','FRESHNESS_CACHE':'../LIFEOS/TOOLS/FreshnessCache','FAILURE_CAPTURE':'../LIFEOS/TOOLS/FailureCapture',
 'KITTY_HOOK':'KittyEnvPersist','ALGORITHM_NUDGE':'AlgorithmNudge','REMINDER_ROUTER':'ReminderRouter',
 'MERGE_SETTINGS':'../LIFEOS/TOOLS/MergeSettings','SETTINGS_BACKPORT':'../LIFEOS/TOOLS/SettingsBackport',
 'WATCHDOG':'../LIFEOS/TOOLS/AgentWatchdog'}.items():
 path=lifeos/'hooks'/(name+('.ts' if name.startswith('../') else '.hook.ts'))
 if not path.exists():raise RuntimeError(str(path))
 env['LIFEOS_'+key+'_PATH']=str(path.resolve())
env['LIFEOS_SESSION_END_HOOK_DIR']=str(lifeos/'hooks')
all_names=[p.stem for p in sorted((repo/'tests').glob('test_*.py'))]
separate={'test_profile_services','test_ownership_setup','test_ownership_setup_host'}
(cache/'separate-modules.json').write_text(json.dumps({'reason':'Actual service manager checks run on isolated development user manager due to measured workstation inotify exhaustion','modules':sorted(separate)},indent=2)+'\n')
names=[name for name in all_names if name not in separate]
env['LIFEOS_COMMAND_HERMES_SOURCE']=str(source/'hermes')
env['LIFEOS_COMMAND_DEPENDENCIES']='/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env'
python='/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
worker=cache/'run-suite.py'
worker.write_text('''import json,signal,sys,unittest,subprocess
from lifeos_hook_bridge import profile_services
original_service_run=profile_services._run
def traced_service_run(*arguments):
 try:
  return original_service_run(*arguments)
 except Exception:
  unit=arguments[-1] if arguments else ''
  row={'arguments':arguments}
  for name,command in [('show',['systemctl','--user','show',unit]),('journal',['journalctl','--user','-u',unit,'-n','30','--no-pager'])]:
   result=subprocess.run(command,capture_output=True,text=True)
   row[name]={'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
  with open(sys.argv[1]+'.service-refusals.jsonl','a') as trace:trace.write(json.dumps(row)+'\\n')
  raise
profile_services._run=traced_service_run
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
previous=str(signal.getsignal(signal.SIGINT))
signal.signal(signal.SIGINT,signal.default_int_handler)
print("INTERRUPT_DEFAULT="+str(signal.getsignal(signal.SIGINT)),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(suite)
with open(sys.argv[1],"w") as output:
 json.dump({"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),"successful":result.wasSuccessful(),"interrupt_before":previous,"failed_cases":[case.id() for case,detail in result.failures+result.errors]},output,indent=2)
 output.write("\\n")
sys.exit(0 if result.wasSuccessful() else 1)
''')
def run(index):
 group=names[index::4]
 command=[python,str(worker),str(cache/f'suite-{index}.json'),*group]
 selected=dict(env,LIFEOS_FRESH_EVIDENCE=str(cache/f'fresh-evidence-{index}'))
 started=time.monotonic()
 with (cache/f'suite-{index}.txt').open('w') as stream:
  result=subprocess.run(command,cwd=repo,env=selected,stdout=stream,stderr=subprocess.STDOUT)
 (cache/f'suite-{index}.done').write_text(str(result.returncode)+'\n')
 return {'index':index,'command':command,'modules':group,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-started,3)}
(cache/'complete-command.json').write_text(json.dumps({'python':python,'source_environment':{key:value for key,value in env.items() if key in ('LIFEOS_HERMES_SOURCE', 'LIFEOS_MEMORY_SOURCE', 'LIFEOS_FRESH_SOURCE', 'LIFEOS_FRESH_EVIDENCE', 'LIFEOS_TASK_HOOK_PATH', 'LIFEOS_PREPARE_HERMES_REPO', 'LIFEOS_PREPARE_LIFEOS_REPO', 'LIFEOS_FRESHNESS_CONTROL_SOURCE', 'LIFEOS_PULSE_SOURCE', 'LIFEOS_TAB_STATE_SOURCE', 'LIFEOS_CONFIG_AUDIT_SOURCE', 'LIFEOS_AGENT_INVOCATION_PATH', 'LIFEOS_HERMES_REBUILD_SOURCE', 'TMPDIR', 'PYTHONPATH')},'module_count':len(names),'group_count':4,'plugin_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()},indent=2)+'\n')
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(run,range(4)))
(cache/'complete-results.json').write_text(json.dumps(results,indent=2)+'\n')
(cache/'complete.done').write_text('0\n' if all(row['exit_code']==0 for row in results) else '1\n')
