# ABOUTME: Traces the normal authenticated activation worker after safely cancelling an incomplete review.
# ABOUTME: Keeps exception reasons private and leaves installed sources, native records, and memory policy unchanged.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or Path.home()!=home:raise RuntimeError('Use the disposable guest owner')
os.umask(0o077)
previous='0d0884787d394664b4ce35da7843d637'
host=profile/'.lifeos-releases/dcd7412c43894a2784c8917977525a3b/hermes'
sys.path.insert(0,str(host))
package=types.ModuleType('portability_cycle_activation_trace')
package.__path__=[str(profile/'plugins/lifeos-release-manager')];sys.modules[package.__name__]=package
workflow=importlib.import_module(package.__name__+'.memory_workflow')
auth=importlib.import_module(package.__name__+'.removal_recovery')
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
owner=auth.authenticate(profile,credentials['username'],credentials['password'],'dashboard:basic:portability-owner')
del credentials
job,request=workflow._job(profile,previous)
status=workflow.read_private(job/'status.json')['state']
if status=='interrupted':
    signature=workflow._review(job,request)['signature']
    workflow.admit(profile,previous,'recover',signature,owner=owner,launch=workflow.launch)
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        status=workflow.read_private(job/'status.json')['state']
        if status=='cancelled':break
        if status=='interrupted':raise RuntimeError('The incomplete activation cannot cancel normally')
        time.sleep(1)
if workflow.read_private(job/'status.json')['state']!='cancelled':raise RuntimeError('Finish the incomplete activation before tracing another')
output=home/'install-input/cycle-activation-trace';output.mkdir(mode=0o700)
def launch(job,unit,action):
    from hermes_cli import _launchers
    worker=Path(workflow.__file__).with_name('memory_workflow_worker.py')
    code='''import json,os
from pathlib import Path
trace_file=Path(sys.argv.pop(1))
def observe(frame,event,argument):
 if event=='exception' and frame.f_code.co_filename.endswith(('ownership_setup.py','memory_owner_access.py','profile_backup.py','memory_backup.py','profile_services.py','memory_activation.py','memory_ownership.py')):
  with trace_file.open('a') as output:
   output.write(json.dumps({'file':Path(frame.f_code.co_filename).name,'function':frame.f_code.co_name,'line':frame.f_lineno,'type':argument[0].__name__,'reason':str(argument[1])})+'\\n')
 return observe
sys.settrace(observe)
worker=sys.argv.pop(1)
sys.argv[0]=worker
runpy.run_path(worker,run_name='__main__')
'''
    command=_launchers.runtime_command(host,[str(output/'exceptions.jsonl'),str(worker),str(job),action],code=code,python=sys.executable)
    command.insert(1,'-B')
    environment={'HOME':str(home),'HERMES_HOME':str(profile),'PATH':os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run(['systemd-run','--user','--collect','--unit='+unit,'--property=UMask=0077',
        *['--setenv='+key+'='+value for key,value in environment.items()],*command],capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError('The diagnostic worker does not start')
result=workflow.queue(profile,request['selection'],owner=owner,launch=launch)
(output/'admission.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
