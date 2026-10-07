# ABOUTME: Records native service properties at actual admission and failure boundaries.
# ABOUTME: Runs real service tests with synthetic user units and no production targets.
import json,os,sys,time,unittest,hashlib,traceback
from pathlib import Path
output=Path(sys.argv[1]); trace=output.with_suffix('.trace.jsonl')
def record(data):
 with trace.open('a') as stream: stream.write(json.dumps({'ts':time.time(),'pid':os.getpid(),**data},default=str)+'\n')
def files(values):
 result={}
 for name in (values or {}).get('FragmentPath','').split()+(values or {}).get('DropInPaths','').split():
  p=Path(name)
  try: result[name]={'realpath':str(p.resolve()),'stat':list(p.stat()),'lstat':list(p.lstat()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  except Exception as e: result[name]={'error':str(e)}
 return result
def observe(frame,event,arg):
 if frame.f_code.co_filename.endswith('/profile_services.py') and frame.f_code.co_name in ('_inspect','_admission') and event in ('return','exception'):
  values=frame.f_locals.get('values')
  record({'function':frame.f_code.co_name,'event':event,'role':frame.f_locals.get('role'),
    'files':files(values),'values':values,'error':str(arg[1]) if event=='exception' else None,
    'profile':str(getattr(frame.f_locals.get('self'),'profile',''))})
 return observe
def audit(event,args):
 if event=='subprocess.Popen' and 'systemctl' in str(args[0]):record({'event':'systemctl','args':args[1],'caller':traceback.format_stack(limit=8)})
sys.addaudithook(audit);sys.settrace(observe)
suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:])
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.settrace(None)
output.write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'failed_cases':[case.id() for case,detail in result.failures+result.errors]},indent=2)+'\n')
sys.exit(0 if result.wasSuccessful() else 1)
