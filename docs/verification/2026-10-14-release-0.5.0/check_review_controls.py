# ABOUTME: Checks qualification identity guards and checkpoint cleanup failure paths.
# ABOUTME: Uses real safe receipts and local fault injection without guest operations.
import argparse,ast,contextlib,io,json,runpy,shutil,subprocess,tempfile,time,traceback
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--pinned')
parser.add_argument('--report',required=True,type=Path)
args=parser.parse_args()
source=Path(__file__).resolve().parent
project=source.parents[2]
def code(name):
 if args.pinned:return subprocess.check_output(['git','show',args.pinned+':'+str((source/name).relative_to(project))],cwd=project,text=True)
 return (source/name).read_text()
results=[]
checks=[('baseline',None,None),
 ('wrong-reboot-source-guest','reboot-verification.json',lambda row:row.update(source_guest=253)),
 ('reboot-production-change','reboot-verification.json',lambda row:row.update(production_guest_changed=True)),
 ('fresh-production-change','stock-first-install.json',lambda row:row.update(production_guest_changed=True)),
 ('whole-production-change','bound-whole-guest-recovery.json',lambda row:row.update(production_guest_changed=True))]
with tempfile.TemporaryDirectory(prefix='lifeos-050-review-controls-') as temporary:
 for name,file,mutation in checks:
  root=Path(temporary)/name/'docs/verification/2026-10-14-release-0.5.0'
  root.mkdir(parents=True)
  for path in source.iterdir():
   if path.is_file() and path.name not in {'RELEASE-CERTIFICATE.json','development-verification.json','development-owner-turn-verification.json'}:shutil.copyfile(path,root/path.name)
  (root/'certify_release.py').write_text(code('certify_release.py'))
  review=root.parents[1]/'agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md'
  review.parent.mkdir(parents=True)
  shutil.copyfile(source.parents[1]/'agents/2026-10-14-pr27-baseline-review/pr27-baseline-review.md',review)
  if mutation:
   path=root/file;row=json.loads(path.read_bytes());mutation(row);path.write_text(json.dumps(row))
  reached=False;failure=None
  with contextlib.redirect_stdout(io.StringIO()):
   try:runpy.run_path(str(root/'certify_release.py'),run_name='__main__')
   except (AssertionError,FileNotFoundError) as error:
    failure=type(error).__name__
    reached=isinstance(error,FileNotFoundError) and str(error.filename).endswith('/development-verification.json')
  created=(root/'RELEASE-CERTIFICATE.json').exists()
  results.append({'case':name,'expected_result_verified':not created and (reached if mutation is None else failure=='AssertionError'),'reached_pending_development_gate':reached,'certificate_created':created})
node=next(item for item in ast.parse(code('protect_development.py')).body if isinstance(item,ast.Try))
class ReceiptView:
 def __init__(self,name='root'):self.name=name
 def __truediv__(self,name):return ReceiptView(name)
 @property
 def parent(self):return self
 def exists(self):return True
 def read_text(self):return '0' if self.name.endswith('process.done') else (source/'bound-whole-guest-recovery.json').read_text()
 def read_bytes(self):return self.read_text().encode()
 def write_text(self,value):writes.append((self.name,value))
for cleanup_fails in (False,True):
 calls=[];writes=[]
 def failed_source(action,label):
  calls.append(label)
  if label=='drain-development':raise RuntimeError('partial-drain-failure')
  if cleanup_fails:raise RuntimeError('cleanup-failure')
 namespace={'root':ReceiptView(),'out':ReceiptView(),'source':failed_source,'run':None,'time':time,'json':json,'result':1,'drained':False,'recovery_required':False,'sys':__import__('sys')}
 caught=None
 with contextlib.redirect_stderr(io.StringIO()):
  try:exec(compile(ast.Module(body=[node],type_ignores=[]),'<checkpoint-control>','exec'),namespace)
  except RuntimeError as error:caught=str(error)
 results.append({'case':'partial-drain-cleanup'+('-also-fails' if cleanup_fails else ''),'expected_result_verified':'recover-development-services' in calls and caught=='partial-drain-failure' and ('process.done','1\n') in writes,'calls':calls,'preserved_failure':caught,'completion_receipt_written':False})
report={'status':'PASS' if all(row['expected_result_verified'] for row in results) else 'FAIL','revision':args.pinned or 'working-tree','results':results,'remote_commands_run':False,'guest_completion_receipts_constructed':False,'control_flow_fault_injection_only':True}
args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['status']=='PASS'
