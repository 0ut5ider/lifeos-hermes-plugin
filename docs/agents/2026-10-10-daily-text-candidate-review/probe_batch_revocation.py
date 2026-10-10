# ABOUTME: Measures authority revocation between real writes in supported native batch publishers.
# ABOUTME: Uses disposable actual owner configurations and records subsequent writes and deletions.
import json, sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryService
kind=sys.argv[1]
if kind=='proposal-gc':
    from test_memory_proposal_gc import MemoryProposalGCTests as Fixture
    from lifeos_hook_bridge import memory_proposal_gc as module
    operation='proposal_gc';arguments={'apply':True,'auto':True,'route':False}
else:
    from test_memory_knowledge_harvest import MemoryKnowledgeHarvestTests as Fixture
    from lifeos_hook_bridge import memory_knowledge_harvest as module
    operation='knowledge_harvest';arguments={'source':'research','dry_run':False,'max_notes':20,'request_id':'synthetic-midpublication-revocation'}
fixture=Fixture();fixture.setUp()
try:
    configuration=fixture.fixture.configuration
    if kind=='proposal-gc':
        second=fixture.root/'LIFEOS/USER/PROJECTS.md'
        second.write_text('## Memory-System Proposals\n- Synthetic expired project rule [SUPERSEDED]\n- Keep current synthetic project rule.\n')
        before={str(p.relative_to(fixture.root)):p.read_text() for p in (fixture.target,second)}
    else:before={'queue':fixture.queue.read_text()}
    original=module.publish
    events=[]
    def publish(path,data):
        original(path,data)
        events.append({'event':'publication','path':str(Path(path).relative_to(fixture.root)),'content':data.decode()})
        if len(events)==1:
            configuration.update(lambda value:value['accounts'].clear())
            events.append({'event':'owner_revoked'})
    module.publish=publish
    try:response=MemoryService(configuration).native(fixture.fixture.context,operation,arguments)
    finally:module.publish=original
    memory=fixture.fixture.fixture.memory
    with memory._transaction() as connection:operations=[dict(row) for row in connection.execute('SELECT * FROM operations')]
    after=({str(p.relative_to(fixture.root)):p.read_text() for p in (fixture.target,second)} if kind=='proposal-gc'
        else {'queue_exists':fixture.queue.exists(),'note_exists':fixture.note.exists(),'state_exists':fixture.state.exists()})
    result={'operation':operation,'response':response,'before':before,'after':after,'events':events,
        'accounts':configuration.load()['accounts'],'journal_exists':memory.transaction.journal.exists(),'operations':operations}
    print(json.dumps(result,indent=2))
    assert response.get('ok') is False,result
    index=next(i for i,e in enumerate(events) if e['event']=='owner_revoked')
    assert any(e['event']=='publication' for e in events[index+1:]),result
    assert not memory.transaction.journal.exists(),result
finally:fixture.doCleanups()
