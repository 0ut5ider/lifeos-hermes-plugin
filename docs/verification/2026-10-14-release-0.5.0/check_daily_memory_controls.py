# ABOUTME: Checks daily synthetic preservation admission against the real safe baseline.
# ABOUTME: Exercises the exact pure validator without guest calls or fabricated completion receipts.
import ast,copy,json
from pathlib import Path
root=Path(__file__).resolve().parent
node=next(item for item in ast.parse((root/'verify_promotion.py').read_text()).body if isinstance(item,ast.FunctionDef) and item.name=='verify_daily_memory')
namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-daily-validator>','exec'),namespace)
baseline=json.loads((root/'daily-memory-baseline.json').read_bytes())
reply={'status':'ok','results':[{'reference':baseline['reference']}]}
cases=[('preserved',lambda b,r:None,True),
 ('absent',lambda b,r:r.update(results=[]),False),
 ('wrong-reference',lambda b,r:r['results'][0].update(reference={'id':'0'*32,'revision':1}),False),
 ('wrong-revision',lambda b,r:r['results'][0]['reference'].update(revision=2),False),
 ('missing-owner',lambda b,r:b.update(authenticated_owner_verified=False),False),
 ('wrong-query',lambda b,r:b.update(synthetic_query='another-query'),False),
 ('data-reset',lambda b,r:b.update(personal_data_imported_or_reset=True),False)]
results=[]
for name,mutation,expected in cases:
 b=copy.deepcopy(baseline);r=copy.deepcopy(reply);mutation(b,r)
 accepted=True
 try:namespace['verify_daily_memory'](b,r)
 except (AssertionError,KeyError,TypeError,ValueError):accepted=False
 results.append({'case':name,'expected_result_verified':accepted==expected})
report={'status':'PASS' if all(x['expected_result_verified'] for x in results) else 'FAIL','cases':len(results),'results':results,'scope':'Pure validator controls only; no guest acceptance or completion receipt'}
(root/'daily-memory-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['status']=='PASS'
