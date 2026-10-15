# ABOUTME: Checks actual public installation stock provenance guards against safe pre-install metadata.
# ABOUTME: Records fail-first and closure controls without guest calls or manufactured completion receipts.
import argparse,ast,copy,hashlib,json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--report',default='stock-provenance-controls.json')
args=parser.parse_args()
project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
body=ast.parse((source/'verify_public_installation.py').read_text()).body
baseline=json.loads((source/'public-stock-baseline.json').read_bytes())
provenance=json.loads((source/'public-stock-source-verification.json').read_bytes())
legacy=json.loads((source/'public-stock-source-initial-limited-verification.json').read_bytes())
function=next((node for node in body if isinstance(node,ast.FunctionDef) and node.name=='validate_stock_provenance'),None)
if function is not None:
    namespace={'json':json,'hashlib':hashlib,'Path':Path}
    for node in body:
        if isinstance(node,ast.Assign):
            try:value=ast.literal_eval(node.value)
            except (ValueError,TypeError):continue
            for target in node.targets:
                if isinstance(target,ast.Name):namespace[target.id]=value
    exec(compile(ast.Module(body=[function],type_ignores=[]),'<actual-stock-provenance-helper>','exec'),namespace)
    validate=namespace['validate_stock_provenance']
else:
    guards=[node for node in body if isinstance(node,ast.Assert) and "baseline['" in ast.unparse(node) and 'model_selection_sha256' not in ast.unparse(node)]
    code=compile(ast.Module(body=guards,type_ignores=[]),'<existing-public-stock-guards>','exec')
    def validate(b,p):exec(code,{'baseline':b})

cases=[('actual-stock-provenance',lambda b,p:None,True),
 ('baseline-wrong-hermes-commit',lambda b,p:b.update(hermes_commit='0'*40),False),
 ('baseline-wrong-source-archive',lambda b,p:b.update(stock_source_sha256='0'*64),False),
 ('source-proof-failed',lambda b,p:p.update(status='FAIL'),False),
 ('source-proof-wrong-commit',lambda b,p:p.update(hermes_commit='0'*40),False),
 ('source-proof-wrong-archive',lambda b,p:p.update(stock_source_sha256='0'*64),False),
 ('source-proof-incomplete-file-set',lambda b,p:p.update(complete_runtime_file_set_verified=False),False),
 ('source-proof-wrong-dashboard',lambda b,p:p.update(dashboard_sha256='0'*64),False),
 ('source-proof-wrong-guest',lambda b,p:p.update(guest=102),False),
 ('legacy-limited-source-proof',lambda b,p:(p.clear(),p.update(legacy)),False)]
results=[]
for name,mutate,expected in cases:
    b=copy.deepcopy(baseline);p=copy.deepcopy(provenance);mutate(b,p);accepted=True
    try:validate(b,p)
    except (AssertionError,KeyError,TypeError,ValueError):accepted=False
    results.append({'case':name,'accepted':accepted,'expected_result_verified':accepted==expected})
report={'status':'PASS' if all(row['expected_result_verified'] for row in results) else 'FAIL',
 'cases':len(results),'actual_helper_present':function is not None,'results':results,
 'scope':'Actual pure helper when present; existing actual baseline guard statements for fail-first baseline otherwise.',
 'real_safe_input_metadata_used':True,'remote_commands_run':False,'guest_completion_receipt_written':False}
Path(__file__).with_name(args.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert report['status']=='PASS'
