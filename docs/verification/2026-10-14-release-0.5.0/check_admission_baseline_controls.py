# ABOUTME: Checks supplementary admission baseline guards against real temporary configuration files.
# ABOUTME: Retains local negative controls without writing a guest receipt or reading personal configuration.
import ast,copy,hashlib,json,sys,tempfile
from pathlib import Path

root=Path(__file__).resolve().parent
nodes=ast.parse((root/'verify_development_admission.py').read_text()).body
stop=next(i for i,n in enumerate(nodes) if isinstance(n,ast.Assert) and "set(baseline['services'])" in ast.unparse(n))
loop=next(i for i,n in enumerate(nodes) if isinstance(n,ast.For))
start=next((i for i,n in enumerate(nodes[:loop]) if isinstance(n,ast.Assert) and "baseline['status']" in ast.unparse(n)),loop)
code=compile(ast.Module(body=nodes[start:stop],type_ignores=[]),'<actual-admission-baseline-guards>','exec')
characterize='--characterize' in sys.argv
results=[]
with tempfile.TemporaryDirectory(prefix='admission-baseline-') as temporary:
 profile=Path(temporary)
 for name in ('.env','lifeos-memory.json','extra.json'):(profile/name).write_bytes(b'synthetic configuration fixture')
 digest=hashlib.sha256(b'synthetic configuration fixture').hexdigest()
 baseline={'status':'PASS','server':'development','model_selection_sha256':'c'*64,
  'configuration_file_sha256':{'.env':digest,'lifeos-memory.json':digest}}
 cases=[('exact-baseline',lambda d:None,True),('empty-digest-map',lambda d:d.update(configuration_file_sha256={}),characterize),
  ('missing-memory-config',lambda d:d['configuration_file_sha256'].pop('lifeos-memory.json'),characterize),
  ('extra-config-key',lambda d:d['configuration_file_sha256'].update({'extra.json':digest}),characterize),
  ('failed-baseline',lambda d:d.update(status='FAIL'),characterize),('wrong-server',lambda d:d.update(server='daily'),characterize),
  ('changed-digest',lambda d:d['configuration_file_sha256'].update({'.env':'0'*64}),False),
  ('invalid-model-digest',lambda d:d.update(model_selection_sha256='invalid'),characterize)]
 for name,mutate,expected in cases:
  current=copy.deepcopy(baseline);mutate(current);accepted=True
  try:exec(code,{'baseline':current,'profile':profile,'hashlib':hashlib})
  except (AssertionError,ValueError,TypeError,KeyError):accepted=False
  results.append({'case':name,'accepted':accepted,'expected_result_verified':accepted==expected})
report={'status':'PASS' if all(r['expected_result_verified'] for r in results) else 'FAIL','cases':len(results),
 'characterization':characterize,'results':results,'remote_commands_run':False,'completion_receipt_constructed':False}
(root/'admission-baseline-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['status']=='PASS'
