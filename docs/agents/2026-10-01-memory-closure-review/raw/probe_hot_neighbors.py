# ABOUTME: Reproduces hot-file drift and source provenance across real native operations.
# ABOUTME: Uses disposable synthetic homes and preserves observed results without changing sources.
import json
from pathlib import Path
import test_memory_native as native
from lifeos_hook_bridge.memory_access import HOT_FILES

OUTPUT=Path(__file__).parent

def run(operation,category,drift):
    fixture=native.NativeMemoryTests(); fixture.setUp()
    try:
        memory=fixture.memory
        first=fixture.remember('RULE: Synthetic target fact','first',category)
        second=fixture.remember('RULE: Synthetic neighboring fact','second',category)
        path=fixture.root/HOT_FILES[category]
        if drift=='overlength':
            changed=path.read_text().replace('RULE: Synthetic neighboring fact','RULE: '+('x'*300))
        elif drift=='valid_addition':
            changed=path.read_text().replace('<!-- END ENTRIES -->','RULE: Synthetic unmanaged neighbor\n<!-- END ENTRIES -->')
        else:
            changed=path.read_text()
        path.write_text(changed)
        before=path.read_text()
        args=[native.OWNER,first['reference']]
        if operation=='correct': args.append('RULE: Synthetic replacement fact')
        args.append('neighbor-'+operation)
        receipt=getattr(memory,operation)(*args)
        after=path.read_text()
        try: read={'result':memory.read_hot(native.OWNER,category)}
        except Exception as error: read={'error_type':type(error).__name__,'error':str(error)}
        with memory._transaction() as connection:
            rows=[dict(row) for row in connection.execute('SELECT * FROM records')]
        result={'operation':operation,'category':category,'drift':drift,'first':first,'second':second,
                'receipt':receipt,'bytes_changed':before!=after,'neighbor_present_after':('x'*300 in after if drift=='overlength' else 'Synthetic unmanaged neighbor' in after),
                'governed_read':read,'rows':rows,'before':before,'after':after}
        return result
    finally: fixture.doCleanups()

def provenance():
    fixture=native.NativeMemoryTests(); fixture.setUp()
    try:
        results=[]
        for category in ('principal','assistant'):
            receipt=fixture.memory.native_add(native.OWNER,{'type':'memory','actor':category,'content':'RULE: Synthetic native source '+category},request_id='native-source-'+category,project='',source_session='synthetic-source-session')
            results.append({'category':category,'receipt':receipt,'recall':fixture.memory.recall(native.OWNER,'Synthetic native source '+category)})
        project=fixture.memory.native_add(native.OWNER,{'type':'knowledge','entity_type':'research','name':'Synthetic native project','content':'Synthetic native project source'},request_id='native-source-project',project='lab',source_session='synthetic-source-session')
        return {'hot':results,'project_control':{'receipt':project,'recall':fixture.memory.recall(native.OWNER,'Synthetic native project source')}}
    finally: fixture.doCleanups()

result={'same_file_mutations':[run(op,category,drift) for op in ('correct','forget') for category in ('principal','assistant') for drift in ('none','overlength','valid_addition')],'native_source_provenance':provenance()}
(OUTPUT/'hot-neighbors-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'cases':[{'operation':r['operation'],'category':r['category'],'drift':r['drift'],'receipt':r['receipt']['status'],'neighbor_present_after':r['neighbor_present_after'],'read_error':r['governed_read'].get('error')} for r in result['same_file_mutations']],'provenance':result['native_source_provenance']},indent=2))
