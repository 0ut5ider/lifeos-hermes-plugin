# ABOUTME: Checks post-admission baseline metadata guards without reading preserved files.
# ABOUTME: Uses a real safe baseline and negative local mutations, never guest completion receipts.
import ast,copy,json,sys
from pathlib import Path

project=Path(__file__).resolve().parents[3]
root=project/'docs/verification/2026-10-14-release-0.5.0'
nodes=ast.parse((root/'verify_development_admission.py').read_text()).body
start=next(i for i,node in enumerate(nodes) if isinstance(node,ast.Assert) and "baseline['status']" in ast.unparse(node))
stop=next(i for i,node in enumerate(nodes[start:],start) if isinstance(node,ast.For) and ast.unparse(node.iter)=="baseline['configuration_file_sha256'].items()")
code=compile(ast.Module(body=nodes[start:stop],type_ignores=[]),'<actual-post-admission-baseline-guards>','exec')
baseline=json.loads((root/'development-prepromotion-baseline.json').read_bytes())
cases=[('actual-safe-baseline',lambda b:None,True),
 ('empty-digest-map',lambda b:b.update(configuration_file_sha256={}),False),
 ('missing-credential-digest',lambda b:b['configuration_file_sha256'].pop('.env'),False),
 ('extra-digest-path',lambda b:b['configuration_file_sha256'].update({'other':'0'*64}),False),
 ('invalid-digest-shape',lambda b:b['configuration_file_sha256'].update({'.env':'invalid'}),False),
 ('failed-baseline',lambda b:b.update(status='FAIL'),False),
 ('wrong-server-baseline',lambda b:b.update(server='daily'),False)]
results=[]
for name,mutate,expected in cases:
 b=copy.deepcopy(baseline);mutate(b);accepted=True
 try:exec(code,{'baseline':b,'Path':Path})
 except (AssertionError,KeyError,TypeError,ValueError):accepted=False
 results.append({'case':name,'accepted':accepted,'expected_result_verified':accepted==expected})
report={'status':'PASS' if all(row['expected_result_verified'] for row in results) else 'FAIL',
        'cases':len(results),'results':results,'scope':'Actual baseline metadata validation statements before preservation file reads',
        'credential_file_read':False,'memory_configuration_file_read':False,
        'guest_completion_receipt_written':False,'remote_commands_run':False}
name=sys.argv[1] if len(sys.argv)>1 else 'post-admission-controls.json'
Path(__file__).with_name(name).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
