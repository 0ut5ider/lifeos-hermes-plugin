# ABOUTME: Checks source-service recovery preserves first failure and always writes failure state.
# ABOUTME: Runs the actual restore finalizer locally with synthetic failures and no guest commands.
import ast,json,sys
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent;s=p/'docs/verification/2026-10-14-release-0.5.0/proxmox_daily_restore.py'
body=ast.parse(s.read_text()).body;outer=next(n for n in body if isinstance(n,ast.Try))
setup=next(n for n in body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='services_code' for t in n.targets))
ns={'package':'/synthetic-package'};exec(compile(ast.Module(body=[setup],type_ignores=[]),'<service-template>','exec'),ns)
results=[]
for obligated in [False,True]:
 for cleanup_fails in [False,True]:
  if not obligated and cleanup_fails:continue
  original=RuntimeError('Original restore failure');calls=[];writes=[]
  class Out:
   def __truediv__(self,key):return self
   def write_text(self,text):writes.append(text)
  def source(code,label):
   calls.append({'label':label,'code':code})
   if cleanup_fails:raise ValueError('Cleanup failure')
  env={'sys':SimpleNamespace(exc_info=lambda:(RuntimeError,original,None)),'source':source,'services_code':ns['services_code'],'recovery_required':obligated,'created':False,'result':1,'out':Out()}
  exec(compile(ast.Module(body=outer.finalbody,type_ignores=[]),'<actual-restore-finalizer>','exec'),env)
  assert len(calls)==int(obligated) and writes==['1\n'] and bool(getattr(original,'__notes__',[]))==cleanup_fails
  if calls:assert 'verify_running()' in calls[0]['code']
  results.append({'obligated':obligated,'cleanup_fails':cleanup_fails,'recovery_called':bool(calls),'failure_marker':'1','original_error':str(original),'notes':getattr(original,'__notes__',[]),'status':'PASS','remote_calls':False,'file_writes':False})
report={'status':'PASS','cases':results};(r/'restore-cleanup-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
