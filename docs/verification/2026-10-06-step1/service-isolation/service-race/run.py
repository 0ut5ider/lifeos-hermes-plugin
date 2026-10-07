# ABOUTME: Measures concurrent disposable service controls before changing admission logic.
# ABOUTME: Retains service manager properties, process identity, test output, and completion.
from pathlib import Path
import concurrent.futures,json,os,subprocess,sys
root=Path(__file__).resolve().parent
namespace={}
exec(Path('/home/outsider/.cache/lifeos-hook-completion-20261006/run-full.py').read_text().split('commands=')[0],namespace)
env=namespace['env'];repo=namespace['repo'];env['TMPDIR']='/home/outsider/.cache/lhc6'
Path(env['TMPDIR']).mkdir(exist_ok=True)
worker=root/'worker.py'
worker.write_text('''# ABOUTME: Records native service properties at actual admission and failure boundaries.
# ABOUTME: Runs real service tests with synthetic user units and no production targets.
import json,os,sys,time,unittest
from pathlib import Path
output=Path(sys.argv[1]); trace=output.with_suffix('.trace.jsonl')
def record(data):
 with trace.open('a') as stream: stream.write(json.dumps({'ts':time.time(),'pid':os.getpid(),**data},default=str)+'\\n')
def observe(frame,event,arg):
 if frame.f_code.co_filename.endswith('/profile_services.py') and frame.f_code.co_name in ('_inspect','_admission') and event in ('return','exception'):
  values=frame.f_locals.get('values')
  record({'function':frame.f_code.co_name,'event':event,'role':frame.f_locals.get('role'),
    'values':values,'error':str(arg[1]) if event=='exception' else None,
    'profile':str(getattr(frame.f_locals.get('self'),'profile',''))})
 return observe
def audit(event,args):
 if event=='subprocess.Popen' and 'systemctl' in str(args[0]):record({'event':'systemctl','args':args[1]})
sys.addaudithook(audit);sys.settrace(observe)
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.settrace(None)
output.write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'failed_cases':[case.id() for case,detail in result.failures+result.errors]},indent=2)+'\\n')
sys.exit(0 if result.wasSuccessful() else 1)
''')
sets=[['test_profile_services'],['test_ownership_setup.OwnershipSetupTests.test_originally_inactive_service_stays_inactive_after_setup_and_return']*5,
 ['test_ownership_setup_host.OwnershipSetupHostTests.test_restarted_profile_uses_native_tools_and_returns_to_preserved_hermes_memory']*5]
commands=[]
def run(index):
 command=[sys.executable,str(worker),str(root/f'{index}.json'),*sets[index]]
 commands.append(command)
 with (root/f'{index}.log').open('w') as stream:
  result=subprocess.run(command,cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT)
 (root/f'{index}.done').write_text(str(result.returncode)+'\n')
 return result.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,range(3)))
(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
(root/'run.done').write_text('0\n' if results==[0,0,0] else '1\n')
