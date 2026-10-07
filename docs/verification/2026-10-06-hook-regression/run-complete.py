# ABOUTME: Runs the complete current test inventory in four isolated regression suites.
# ABOUTME: Retains commands, source bindings, signal state, results, and completion markers.
from pathlib import Path
import concurrent.futures
import json
import os
import signal
import subprocess
import time

cache=Path('/home/outsider/.cache/lifeos-hook-completion-20261006')
namespace={}
exec((cache/'run-full.py').read_text().split('commands=')[0],namespace)
repo=namespace['repo'];env=namespace['env']
env['LIFEOS_FRESH_SOURCE']=str(cache/'installer-candidate')
env['LIFEOS_HERMES_REBUILD_SOURCE']=str(cache/'prepared-all-final/hermes')
names=[p.stem for p in sorted((repo/'tests').glob('test_*.py'))]
python='/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
worker=cache/'run-suite.py'
worker.write_text('''import json,signal,sys,unittest
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
