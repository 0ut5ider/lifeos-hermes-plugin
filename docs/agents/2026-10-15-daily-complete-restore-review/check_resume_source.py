# ABOUTME: Checks continuation proves source recovery and actual application service status.
# ABOUTME: Runs the exact local resume branch and service helper with synthetic boundaries only.
import argparse,ast,contextlib,io,json
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--before',action='store_true');parser.add_argument('--require-fixed',action='store_true');args=parser.parse_args()
s=r/'proxmox_daily_restore.before.py' if args.before else p/'docs/verification/2026-10-14-release-0.5.0/proxmox_daily_restore.py'
body=ast.parse(s.read_text()).body
outer=next(n for n in body if isinstance(n,ast.Try))
branch=next(n for n in outer.body if isinstance(n,ast.If) and ast.unparse(n.test)=='args.resume_backup')
setup=next(n for n in body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='services_code' for t in n.targets))
service_ns={'package':'/synthetic-package'};exec(compile(ast.Module(body=[setup],type_ignores=[]),'<actual-services-template>','exec'),service_ns)
results=[]
for case in ['already-running','needs-recovery','recovery-still-required','inactive-service']:
 calls=[];observed=[];status={'recovery_required':case in ['needs-recovery','recovery-still-required']}
 class Evidence:
  def __truediv__(self,n):return self
  def read_text(self):return json.dumps([{'ctime':1,'volid':'PBS-01:backup/ct/102/synthetic'}])
 def resume():
  calls.append('native-resume')
  if case!='recovery-still-required':status['recovery_required']=False
 def run(argv,**options):
  calls.append(argv[3]);return SimpleNamespace(stdout='ActiveState=inactive\nSubState=dead\n' if case=='inactive-service' else 'ActiveState=active\nSubState=running\n')
 ns={'args':SimpleNamespace(resume_backup=True),'backup_evidence':Evidence(),'json':json,'services_code':service_ns['services_code'],'recovery_required':False}
 def source(code,label):
  calls.append(label);observed.append(ns['recovery_required'])
  nodes=ast.parse(code).body
  start=next(i for i,n in enumerate(nodes) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='s' for t in n.targets))+1
  env={'s':SimpleNamespace(status=lambda:dict(status),resume=resume),'subprocess':SimpleNamespace(run=run)}
  with contextlib.redirect_stdout(io.StringIO()):exec(compile(ast.Module(body=nodes[start:],type_ignores=[]),'<actual-source-recovery-action>','exec'),env)
 ns['source']=source;error=None
 try:exec(compile(ast.Module(body=[branch],type_ignores=[]),'<actual-resume-backup-branch>','exec'),ns)
 except (AssertionError,RuntimeError) as e:error=type(e).__name__
 expected=(error is None and ns['recovery_required'] is False and len([x for x in calls if x.endswith('.service')])==3) if case in ['already-running','needs-recovery'] else (error is not None and ns['recovery_required'] is True)
 expected=expected and observed==[True]
 results.append({'case':case,'status':'PASS' if expected else 'FAIL','calls':calls,'obligation_at_source_call':observed,'remaining_recovery_obligation':ns['recovery_required'],'error_type':error,'remote_calls':False,'private_inputs_used':False})
report={'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL','cases':results}
label='before' if args.before else 'after';(r/('resume-source-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if args.require_fixed:assert report['status']=='PASS'
