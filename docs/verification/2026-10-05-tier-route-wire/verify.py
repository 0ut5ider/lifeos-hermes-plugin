# ABOUTME: Checks the retained tier route results against the release effort mapping.
# ABOUTME: Requires one successful private model request per tier with the mapped effort on the wire.
import json
from pathlib import Path

root=Path(__file__).resolve().parent
expected={'haiku':'low','sonnet':'medium','opus':'xhigh','fable':'xhigh'}
document=json.loads((root/'tier-results.json').read_text())
assert (root/'run.done').read_text().strip()=='0'
assert document['mapping']==expected
assert [row['tier'] for row in document['tiers']]==list(expected)
for row in document['tiers']:
    assert row['exit_code']==0 and row['stderr']=='' and row['generation_requests']==1,row['tier']
    assert '--effort' in row['command'] and row['command'][row['command'].index('--effort')+1]=='medium'
    request,=row['requests']
    assert request['path']=='/v1/chat/completions' and request['upstream_status']==200
    assert request['effort_fields']=={'reasoning_effort':expected[row['tier']]},row['tier']
    assert request['body_keys']==['messages','model','reasoning_effort']
    assert request['requested_model']=='lifecycle-fixture' and request['actual_model']
    output=json.loads(row['stdout'])
    assert output['result']=='READY' and output['is_error'] is False
    assert list(output['modelUsage'])==[request['actual_model']]
print(json.dumps({'verified_tiers':len(document['tiers'])}))
