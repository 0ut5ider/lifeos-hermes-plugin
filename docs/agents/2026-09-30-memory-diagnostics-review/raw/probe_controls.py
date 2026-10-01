# ABOUTME: Exercises diagnostic owner statistics, retained samples, and denied contexts.
# ABOUTME: Runs real native CLI and governed service calls in isolated fixtures.
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import json
from test_memory_diagnostics import MemoryDiagnosticTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryService

def emit(name, **values): print(json.dumps({'case':name,**values}),flush=True)
c=MemoryDiagnosticTests(); c.setUp()
try:
    service=MemoryService(c.fixture.configuration)
    c.write('reviewer-runs.jsonl',[c.reviewer(ok=True,inference_duration_ms=n,dispatch_summary={'by_type':{'knowledge':2,'idea':1,'proposal':3}}) for n in (10,20,30,40)])
    c.write('memory-writes.jsonl',[{'ts':c.now,'file':'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md','new_count':9,'prior_count':2}])
    c.write('memory-health.jsonl',[{'ts':c.now,'overall':'ok','counts':{'critical':0,'warn':0,'ok':3}}])
    c.write('pending-proposals.jsonl',[c.proposal('Synthetic current sample',status='accepted'),c.proposal('Synthetic outside window',ts=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat())])
    managed=c.call('MemoryInsights.ts','--days','7').stdout
    connector=c.root/'LIFEOS/USER/CONFIG/memory-access.json'; cfg=connector.read_bytes();connector.unlink()
    unmanaged=c.call('MemoryInsights.ts','--days','7',context=False).stdout
    connector.write_bytes(cfg);connector.chmod(0o600)
    assert managed==unmanaged,(managed,unmanaged)
    emit('stats-parity',identical=True,managed=managed,unmanaged=unmanaged)
    context=c.fixture.context
    c.fixture.context=replace(context,model_route='unapproved')
    denied=c.call('MemoryInsights.ts').stdout
    assert 'unavailable' in denied.lower()
    emit('changed-route',stdout=denied)
    c.fixture.context=context
    connector.unlink();connector.symlink_to(connector.parent/'missing-synthetic-config')
    denied=c.call('MemoryStatus.ts','--json').stdout
    assert 'unavailable' in denied.lower()
    emit('dangling-connector',stdout=denied)
    connector.unlink();connector.write_bytes(cfg);connector.chmod(0o600)
    saved=c.fixture.fixture.remember('RULE: Synthetic superseded diagnostic quote','correction-source','principal')
    result=c.fixture.fixture.memory.correct(OWNER,saved['reference'],'RULE: Synthetic replacement diagnostic quote','diagnostic-correct')
    assert result['status']=='committed'
    c.now=datetime.now(timezone.utc).isoformat()
    path=c.write('pending-proposals.jsonl',[c.proposal('Synthetic superseded diagnostic quote'),c.proposal('Synthetic current decoded control',id='current')])
    text=path.read_text();text=text.replace('Synthetic superseded diagnostic quote',''.join('\\u%04x'%ord(char) for char in 'Synthetic superseded diagnostic quote'));path.write_text(text)
    output=c.call('MemoryInsights.ts').stdout
    assert 'Synthetic superseded diagnostic quote' not in output and 'Synthetic current decoded control' in output
    assert 'Proposals (2 total in window)' in output
    emit('superseded-unicode-json',stdout=output)
    for bad in (None,15,str(c.root/'LIFEOS/USER/CONFIG/memory-access.json')):
        result=service.native(context,'read_diagnostic',{'path':bad});assert result['ok'] is False
        emit('invalid-path',path=bad,result=result)
    # Enough valid numeric-only projected rows to cross the documented service cap.
    c.write('reviewer-runs.jsonl',[c.reviewer()]*30000)
    result=service.native(context,'read_diagnostic',{'path':str(c.obs/'reviewer-runs.jsonl')})
    assert result['ok'] is False and 'limit' in result['message']
    output=c.call('MemoryStatus.ts','--json').stdout
    assert 'unavailable' in output
    emit('documented-over-limit',result=result,stdout=output)
finally:c.doCleanups()
