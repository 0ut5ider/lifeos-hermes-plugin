# ABOUTME: Records native session consolidation when owner authority changes during publication.
# ABOUTME: Uses a real transcript and native extraction in a disposable configured owner fixture.
import json, sys
from dataclasses import replace
from pathlib import Path
from test_memory_session_harvest import MemorySessionHarvestTests
from lifeos_hook_bridge import memory_session_harvest as harvest
from lifeos_hook_bridge.memory_service import MemoryService
fixture=MemorySessionHarvestTests();fixture.setUp()
try:
    fixture.write_transcript('Actually, I meant to use the synthetic safe port for the lab. We decided to use the synthetic safe port. The decision is to keep that port for the lab service.')
    rows=[{'type':'user','sessionId':fixture.session,'timestamp':f'2026-10-08T12:0{i}:00+00:00','message':{'role':'user','content':text}} for i,text in enumerate(('We decided to use the synthetic safe port. The decision is to keep that port for the lab service.','We decided to keep synthetic event receipts. The decision is to retain receipts for the lab service.'))]
    fixture.transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    configuration=fixture.fixture.configuration
    mining='--default' not in sys.argv
    if not mining:
        fixture.write_transcript('Actually, I meant to use the synthetic safe port for this lab.')
        second=replace(fixture.context,session_id='synthetic-second-session')
        from lifeos_hook_bridge.memory_runtime import MemoryRuntime
        from lifeos_hook_bridge.memory_transaction import publish
        runtime=MemoryRuntime(configuration.path)
        with fixture.fixture.fixture.memory._transaction() as connection:
            state=runtime._stamp(configuration.load(),second,connection)
        states=json.loads(runtime.state_path.read_text());states[second.session_id]=state
        publish(runtime.state_path,json.dumps(states).encode())
        row={'type':'user','sessionId':second.session_id,'timestamp':'2026-10-08T12:01:00+00:00',
            'message':{'role':'user','content':'Actually, I meant to keep synthetic receipts for this lab.'}}
        publish(fixture.transcripts/(second.session_id+'.jsonl'),(json.dumps(row)+'\n').encode())
    original=harvest.publish
    events=[]
    def observe(path,data):
        original(path,data)
        events.append({'event':'publication','path':str(Path(path).relative_to(fixture.root)), 'body':data.decode()})
        if len(events)==1:
            configuration.update(lambda value:value['accounts'].clear())
            events.append({'event':'owner_revoked'})
    harvest.publish=observe
    try:
        response=MemoryService(configuration).native(fixture.context,'session_harvest',
            {'recent':20,'all':False,'session':None,'projects_dir':None,'dry_run':False,'mine':mining})
    finally:harvest.publish=original
    memory=fixture.fixture.fixture.memory
    with memory._transaction() as connection:operations=[dict(row) for row in connection.execute('SELECT * FROM operations')]
    result={'response':response,'events':events,'current_accounts':configuration.load()['accounts'],
        'learning_files':[str(p.relative_to(fixture.root)) for p in fixture.notes()],
        'candidate_files':[str(p.relative_to(fixture.root)) for p in (fixture.root/'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue').glob('*.json')],
        'journal_exists':memory.transaction.journal.exists(),'operations':operations}
    print(json.dumps(result,indent=2))
    assert response.get('ok') is False,result
    index=next(i for i,e in enumerate(events) if e['event']=='owner_revoked')
    assert any(e['event']=='publication' for e in events[index+1:]),result
    assert not memory.transaction.journal.exists(),result
finally:fixture.doCleanups()
