# ABOUTME: Checks the actual source retry preflight refuses changed synthetic fixture files.
# ABOUTME: Redirects only the fixed fixture root to local synthetic data and never runs Atlas recovery.
import ast,contextlib,copy,hashlib,io,json,os,stat,tempfile
from pathlib import Path
r=Path(__file__).resolve().parent;s=r/'atlas-reuse/proxmox_daily_restore.py';tree=ast.parse(s.read_text())
sourcecall=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='source' and len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='check-existing-synthetic-atlas')
expected={'status':'PASS','action':'prepare','version':'0.5.0','cases':[{'case':'baseline','files':51,'archives':1,'journal_present':False},{'case':'interrupted','files':55,'archives':2,'journal_present':True},{'case':'later-edit','files':55,'archives':2,'journal_present':True}],'personal_data_used':False,'live_store_modified':False}
text=eval(compile(ast.Expression(sourcecall.args[0]),'<actual-readonly-source-code>','eval'),{'preparation':{'report':expected}})
labels=['positive','content-changed','mode-changed','symlink','map-omission','outside-home-path','wrong-home','wrong-case','boolean-receipt-count','wrong-receipt-count','missing-file']
results=[]
with tempfile.TemporaryDirectory(prefix='atlas-retry-',dir=r) as temporary:
 for label in labels:
  folder=Path(temporary)/label;folder.mkdir();report=copy.deepcopy(expected);first=None;first_prepared=None
  for row in report['cases']:
   case=folder/row['case'];home=case/'home';home.mkdir(parents=True);captured={}
   for i in range(row['files']):
    path=home/(str(i)+'.synthetic');path.write_text('Synthetic archived fixture '+str(i)+'\n');path.chmod(0o600)
    captured[str(path)]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mode':0o600}
    if first is None:first=path
   prepared={'case':row['case'],'home':str(home),'captured':captured};(case/'prepared.json').write_text(json.dumps(prepared))
   if first_prepared is None:first_prepared=case/'prepared.json'
  if label=='content-changed':first.write_text('Changed fixture')
  if label=='mode-changed':first.chmod(0o644)
  if label=='symlink':
   other=first.with_name('other.synthetic');first.rename(other);first.symlink_to(other)
  if label=='missing-file':first.unlink()
  data=json.loads(first_prepared.read_bytes())
  if label=='map-omission':data['captured'].pop(str(first))
  if label=='outside-home-path':
   old=data['captured'].pop(str(first));data['captured'][str(folder/'outside.synthetic')]=old
  if label=='wrong-home':data['home']=str(folder/'other-home')
  if label=='wrong-case':data['case']='interrupted'
  first_prepared.write_text(json.dumps(data))
  if label=='boolean-receipt-count':report['cases'][0]['archives']=True
  if label=='wrong-receipt-count':report['cases'][0]['archives']=2
  (folder/'prepare.json').write_text(json.dumps(report))
  parsed=ast.parse(text)
  class RootBoundary(ast.NodeTransformer):
   def visit_Constant(self,node):
    if node.value=='/home/lifeos-hermes/deployment/history-recovery-0.5.0-04efe633':return ast.copy_location(ast.Constant(str(folder)),node)
    return node
  parsed=ast.fix_missing_locations(RootBoundary().visit(parsed));accepted=True;error=None
  try:
   with contextlib.redirect_stdout(io.StringIO()):exec(compile(parsed,'<actual-readonly-fixture-preflight>','exec'),{})
  except (AssertionError,OSError,ValueError,TypeError) as exc:accepted=False;error=type(exc).__name__
  assert accepted==(label=='positive'),label
  results.append({'case':label,'accepted':accepted,'error_type':error,'status':'PASS','source_root_boundary_redirected':True,'native_prepare_or_verify_run':False,'personal_inputs_used':False})
result={'status':'PASS','cases':results,'remote_calls':False,'guest_receipts_created':False}
(r/'atlas-readonly-preflight-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
