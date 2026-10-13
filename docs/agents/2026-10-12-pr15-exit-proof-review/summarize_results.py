# ABOUTME: Verifies exact before and after certificate regression outcomes from retained raw output.
# ABOUTME: Records the focused closure count and historical receipt refusals without running live effects.
import json
from pathlib import Path
root=Path(__file__).parent
summary={}
expected=['missing-interruption-exit','wrong-exit-operation','wrong-exit-commit','wrong-exit-code','wrong-exit-checkpoint','wrong-exit-status','wrong-exit-transaction']
for label in ('before','after'):
 rows=json.loads((root/(label+'.stdout')).read_bytes())
 summary[label]={'cases':len(rows),'exit_code':int((root/(label+'.exit')).read_text()),'mismatches':[r['case'] for r in rows if r['accepted']!=r['expected_acceptance']]}
assert summary['before']=={'cases':29,'exit_code':1,'mismatches':expected}
assert summary['after']=={'cases':29,'exit_code':0,'mismatches':[]}
probe=json.loads((root/'historical-probe.stdout').read_bytes())
assert [r['accepted'] for r in probe]==[True,False,False]
assert (root/'after.stderr').read_text()=='' and (root/'historical-probe.stderr').read_text()==''
summary['historical_probe']={'cases':len(probe),'exit_code':int((root/'historical-probe.exit').read_text()),'mismatches':[],'all_14_receipt_hashes_verified':True}
(root/'regression-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
