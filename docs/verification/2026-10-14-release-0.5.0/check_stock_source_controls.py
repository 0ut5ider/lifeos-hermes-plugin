# ABOUTME: Checks complete stock runtime admission with actual immutable source and dashboard archives.
# ABOUTME: Executes only validator statements with local mutations and writes no guest acceptance receipts.
import ast,json,shutil,tarfile,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
cache=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014')
stock=cache/'stock-source.tar'
frontend=Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/hermes-dashboard.tgz')
body=ast.parse((root/'verify_public_stock_source.py').read_text()).body
stop=next(i for i,x in enumerate(body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='report' for t in x.targets))
body=body[:stop]
results=[]
for name in ('exact-archives','extra-startup-source','extra-symlink','extra-bytecode','altered-source','altered-dashboard'):
 with tempfile.TemporaryDirectory(prefix='lifeos-stock-source-control-') as temporary:
  home=Path(temporary);stage=home/'releases/qualification-0.5.0';stage.mkdir(parents=True)
  shutil.copyfile(root/'stock-source.json',stage/'stock-source.json')
  (home/'releases/stock-source.tar').symlink_to(stock)
  (home/'releases/hermes-dashboard.tgz').symlink_to(frontend)
  runtime=home/'runtime/stock-hermes';runtime.mkdir(parents=True)
  for archive in (stock,frontend):
   with tarfile.open(archive) as reader:reader.extractall(runtime,filter='data')
  if name=='extra-startup-source':(runtime/'sitecustomize.py').write_text('extra = True\n')
  if name=='extra-symlink':(runtime/'sitecustomize.py').symlink_to('run_agent.py')
  if name=='extra-bytecode':(runtime/'extra.pyc').write_bytes(b'extra')
  if name=='altered-source':(runtime/'run_agent.py').write_text('changed = True\n')
  if name=='altered-dashboard':(runtime/'hermes_cli/web_dist/index.html').write_text('changed frontend')
  nodes=ast.parse((root/'verify_public_stock_source.py').read_text()).body[:stop]
  for node in nodes:
   if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='home' for t in node.targets):node.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(home))],keywords=[])
  rejected=False
  try:exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'<actual-stock-source-validation>','exec'),{})
  except AssertionError:rejected=True
  results.append({'case':name,'expected_result_verified':rejected==(name!='exact-archives'),'rejected':rejected})
report={'status':'PASS' if all(r['expected_result_verified'] for r in results) else 'FAIL','cases':len(results),'results':results,'guest_completion_receipt_written':False,'remote_commands_run':False}
(root/'stock-source-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['status']=='PASS'
