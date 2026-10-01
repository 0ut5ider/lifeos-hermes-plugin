# ABOUTME: Compares explicit tool source attribution with native tool attribution in one context.
# ABOUTME: Uses authenticated synthetic sessions, actual native persistence, and registry readback.
import json
from pathlib import Path
import test_memory_delegation as delegation
from lifeos_hook_bridge.memory_service import MemoryService
from test_memory_native import OWNER
out=Path(__file__).parent
f=delegation.MemoryDelegationTests();f.setUp()
try:
    service=MemoryService(f.configuration)
    results=[]
    for category in ('principal','assistant','project'):
        arguments={'category':category,'content':'RULE: Synthetic explicit source '+category if category!='project'
            else 'Synthetic explicit source project','title':'Synthetic explicit source','project':'general','request_id':'explicit-'+category}
        receipt=service.call_context(f.context,'lifeos_memory_remember',arguments)
        assert receipt['status']=='committed',receipt
        recalled=f.fixture.memory.get(OWNER,receipt['reference'])
        results.append({'category':category,'receipt':receipt,'record':recalled})
    native=service.native(f.context,'add',{'item':{'type':'memory','actor':'principal','content':'RULE: Synthetic native provenance control'},
        'request_id':'native-control','project':'general','observed_revision':''})
    assert native['ok'],native
    result={'context_session':f.context.session_id,'context_writer':f.context.transport+':'+f.context.author,
        'explicit':results,'native_control':native,'native_readback':f.fixture.memory.recall(OWNER,'native provenance control')}
    (out/'explicit-context-provenance-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:f.doCleanups()
