# ABOUTME: Checks destructive cleanup gates against actual operator control flow with local boundaries.
# ABOUTME: Records commands in memory and never calls Proxmox, deletes guests, or writes guest receipts.
import argparse,ast,contextlib,io,json,re,sys
from pathlib import Path
from types import SimpleNamespace
r=Path(__file__).resolve().parent;p=r.parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--before',action='store_true');parser.add_argument('--require-fixed',action='store_true');args=parser.parse_args()
s=r/'cleanup_release_guests.historical-guard-shape.py' if args.before else p/'docs/verification/2026-10-14-release-0.5.0/cleanup_release_guests.py'
body=ast.parse(s.read_text()).body;selected=[n for n in body if isinstance(n,(ast.FunctionDef,ast.Assign))]
results=[]
for label in ['positive','redirected-storage','wrong-storage-type','symlink-storage','wrong-removal-command','unprotected-archive','restore-not-pass','wrong-source','wrong-restore-id','wrong-version','wrong-commit','wrong-sha','incomplete-process','missing-removal-op','duplicate-removal-op','failed-removal-op','boolean-removal-exit','wrong-archive-prefix','restore-guest-present','missing-owned-guest','changed-guest-config']:
 calls=[];owned={111:'lifeos-050-daily-rehearsal',112:'lifeos-050-fresh-rehearsal',113:'lifeos-050-public-install'};remaining=set(owned);stopped=set();writes=[]
 proof={'status':'PASS','version':'0.5.0','source_guest':102,'restored_guest':110,'program_commit':'04efe633296eb2b1a1d95561ca6d3e9516cd47dc','archive_sha256':'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813','archive':'PBS-01:backup/ct/102/synthetic-test-archive'}
 ops=[{'label':'destroy-disposable','exit_code':0,'command':['pct','destroy','110','--purge','1']}]
 if label=='wrong-removal-command':ops[0]['command']=['pct','status','110']
 if label=='restore-not-pass':proof['status']='FAIL'
 if label=='wrong-source':proof['source_guest']=111
 if label=='wrong-restore-id':proof['restored_guest']=114
 if label=='wrong-version':proof['version']='0.4.3'
 if label=='wrong-commit':proof['program_commit']='0'*40
 if label=='wrong-sha':proof['archive_sha256']='0'*64
 if label=='missing-removal-op':ops=[]
 if label=='duplicate-removal-op':ops*=2
 if label=='failed-removal-op':ops[0]['exit_code']=1
 if label=='boolean-removal-exit':ops[0]['exit_code']=False
 if label=='wrong-archive-prefix':proof['archive']='PBS-01:backup/ct/111/synthetic-test-archive'
 if label=='missing-owned-guest':remaining.remove(112)
 class Evidence:
  def __init__(self,key=''):self.key=key
  def __truediv__(self,key):return Evidence(key)
  def read_bytes(self):return json.dumps(proof if self.key=='verification.json' else ops).encode()
  def read_text(self):return '1\n' if label=='incomplete-process' else '0\n'
 class Output:
  def with_suffix(self,suffix):return self
  def exists(self):return False
  def write_text(self,value):writes.append(value)
 class Directory:
  def __init__(self,value):self.value=value
  def resolve(self):return Directory('/synthetic/redirected') if label=='symlink-storage' else self
  def __eq__(self,other):return isinstance(other,Directory) and other.value==self.value
  def is_dir(self):return True
  def is_symlink(self):return label=='symlink-storage'
  def rglob(self,p):return []
  def rmdir(self):calls.append(['local-rmdir',self.value])
 class ArgumentParser:
  def add_argument(self,*a,**k):pass
  def parse_args(self):return SimpleNamespace(evidence=Evidence(),out=Output())
 def run(argv,**options):
  calls.append(argv)
  result=''
  if argv[:3]==['pvesh','get','/cluster/resources']:
   result=json.dumps(([{'vmid':110,'type':'lxc','name':'not-removed','status':'stopped'}] if label=='restore-guest-present' else [])+[{'vmid':102,'type':'lxc','name':'daily','status':'running'},{'vmid':801,'type':'qemu','name':'processing','status':'running'}]+[{'vmid':x,'type':'lxc','name':owned[x],'status':'stopped' if x in stopped else 'running'} for x in sorted(remaining)])
  elif argv[:2]==['pct','config']:
   guest=int(argv[2]);hostname='foreign-guest' if label=='changed-guest-config' and guest==112 else owned[guest];result=f'hostname: {hostname}\ntags: disposable;lifeos-test\nrootfs: lifeos-050-tests:{guest}/vm-{guest}-disk-0.raw,size=120G\n'
  elif argv[:2]==['pct','shutdown']:stopped.add(int(argv[2]))
  elif argv[:2]==['pct','status']:result='status: stopped\n'
  elif argv[:2]==['pct','destroy']:remaining.remove(int(argv[2]))
  elif argv[:3]==['pvesh','get','/storage/lifeos-050-tests']:
   result=json.dumps({'type':'zfspool' if label=='wrong-storage-type' else 'dir','path':'/synthetic/unowned' if label=='redirected-storage' else '/var/lib/vz/lifeos-050-tests','storage':'lifeos-050-tests'})
  elif argv[:2]==['pvesh','get'] and '/storage/lifeos-050-tests/content' in argv[2]:result='[]'
  elif argv[:2]==['pvesh','get'] and '/storage/PBS-01/content/' in argv[2]:result=json.dumps({'protected':label!='unprotected-archive'})
  else:
   assert argv==['pvesm','remove','lifeos-050-tests'],argv
  return SimpleNamespace(stdout=result,returncode=0,check_returncode=lambda:None)
 ns={'argparse':SimpleNamespace(ArgumentParser=ArgumentParser),'Path':Directory,'json':json,'re':re,'subprocess':SimpleNamespace(run=run)}
 exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual-cleanup-operator>','exec'),ns)
 accepted=True;error=None
 try:
  with contextlib.redirect_stdout(io.StringIO()):ns['main']()
 except (AssertionError,KeyError,TypeError,ValueError) as exc:accepted=False;error=type(exc).__name__
 destroys=[x for x in calls if x[:2]==['pct','destroy']]
 correct=(accepted and [int(x[2]) for x in destroys]==[111,112,113]) if label=='positive' else (not accepted and not destroys)
 results.append({'case':label,'status':'PASS' if correct else 'FAIL','operator_accepted':accepted,'error_type':error,'destructive_commands_before_refusal':destroys,'calls':calls,'local_boundary_only':True,'remote_commands_executed':False,'guest_receipts_written':False})
report={'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL','cases':results}
which='before' if args.before else 'after';(r/('cleanup-boundaries-'+which+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if args.require_fixed:assert report['status']=='PASS'
