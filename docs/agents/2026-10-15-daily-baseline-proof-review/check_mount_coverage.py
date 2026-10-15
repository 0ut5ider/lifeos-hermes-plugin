# ABOUTME: Shows native journal subsets need strict seven-target coverage in daily evidence.
# ABOUTME: Executes actual native manifest and current caller guards on synthetic journals only.
import ast,hashlib,json,os,stat,tempfile
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent
native=ast.parse((p/'lifeos_hook_bridge/mount_transaction.py').read_text())
klass=next(n for n in native.body if isinstance(n,ast.ClassDef) and n.name=='MountTransaction')
method=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_manifest')
read=next(n for n in native.body if isinstance(n,ast.FunctionDef) and n.name=='_read')
files=next(ast.literal_eval(n.value) for n in native.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FILES' for t in n.targets))
class MountError(RuntimeError):pass
ns={'Path':Path,'os':os,'stat':stat,'hashlib':hashlib,'json':json,'LIMIT':4*1024*1024,'FILES':files,'PENDING':{'prepared','applying','restoring'},'MountError':MountError}
exec(compile(ast.Module(body=[read,method],type_ignores=[]),'<actual-native-manifest>','exec'),ns)
source=p/'docs/verification/2026-10-14-release-0.5.0/verify_daily_restored_programs.py';tree=ast.parse(source.read_text())
start=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='manifest' for t in n.targets))+1
end=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='journal_digest' for t in n.targets))
guards=tree.body[start:end];old=[n for n in guards if not isinstance(n,ast.Assert) or 'expected_mount_targets' not in ast.unparse(n)]
results=[]
with tempfile.TemporaryDirectory(prefix='mount-coverage-',dir=r) as temp:
 home=Path(temp);profile=home/'.hermes';installed=home/'.claude';profile.mkdir();installed.mkdir();state=home/'state';state.mkdir(mode=0o700);snapshot=state/('a'*32);snapshot.mkdir(mode=0o700);journal=state/'journal.json';baseline=home/'baseline.json'
 self=SimpleNamespace(journal=journal,profile=profile,installed=installed,baseline=baseline,state=state,_workspace=lambda value:None)
 for label,names in [('all-seven',list(files)),('missing-output',list(files)[:-1]),('extra-baseline',list(files)+['BASELINE'])]:
  entries=[{'target':str(baseline if n=='BASELINE' else profile/n),'before':None,'after':{'digest':'a'*64,'mode':0o600},'copy':i} for i,n in enumerate(names)]
  value={'version':1,'profile':str(profile),'installed':str(installed),'baseline':str(baseline),'snapshot':str(snapshot),'state':'committed','binding':None,'retain_for_rollback':False,'entries':entries,'absent_directories':[],'workspace':str(home/'workspace')}
  journal.write_text(json.dumps(value));journal.chmod(0o600);manifest=ns['_manifest'](self)
  env={'manifest':manifest,'profile':profile,'current':SimpleNamespace(memory_module=lambda name:SimpleNamespace(FILES=files)),'worker':SimpleNamespace(restore_available=lambda *a:False),'job':None,'request':None,'plan':None}
  exec(compile(ast.Module(body=old,type_ignores=[]),'<previous-observed-caller-guard-shape>','exec'),env)
  accepted=True
  try:exec(compile(ast.Module(body=guards,type_ignores=[]),'<actual-current-caller-guards>','exec'),env)
  except AssertionError:accepted=False
  assert accepted==(label=='all-seven')
  results.append({'case':label,'native_manifest_accepts':True,'previous_caller_guard_shape_accepts':True,'current_caller_accepts':accepted,'expected_result_verified':True})
report={'status':'PASS','cases':results,'scope':'Native manifest parser plus exact current evidence guards. Previous guard shape excludes only the newly added target coverage assertion. Synthetic files only.','remote_calls':False}
(r/'mount-coverage-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
