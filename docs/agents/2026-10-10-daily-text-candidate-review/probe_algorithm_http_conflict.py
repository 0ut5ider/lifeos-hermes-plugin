# ABOUTME: Reproduces detected but unrecoverable Algorithm publication through native HTTP.
# ABOUTME: Runs disposable authenticated servers and schedules one actual concurrent source edit.
import json, importlib
from pathlib import Path
import httpx
from test_memory_algorithm_edits import MemoryAlgorithmEditTests
from lifeos_hook_bridge.memory_access import NativeMemory
fixture=MemoryAlgorithmEditTests()
fixture.setUp()
try:
    directory=fixture.root/'LIFEOS/ALGORITHM'
    initial={name:(directory/name).read_bytes() for name in ('LATEST','changelog.md','v3.2.1.md')}
    fixture.fixture.login()
    fixture.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
    module=importlib.import_module('lifeos_memory_settings.memory_algorithm_edit')
    original=module.publish
    publications=[]
    def concurrent(path,data):
        original(path,data)
        if Path(path).is_relative_to(fixture.root):publications.append(str(Path(path).relative_to(fixture.root)))
        if Path(path)==directory/'LATEST':(directory/'v3.2.1.md').write_text('Synthetic later concurrent source edit.\n')
    module.publish=concurrent
    try:
        with httpx.Client(timeout=45) as client:
            fixture.login(client)
            response=client.post(fixture.native+'/api/algorithm-tab/doctrine',json={
                'content':'# The Algorithm 3.2.1\n\n'+'Synthetic requested next doctrine. '*30,
                'bump':'patch','note':'Synthetic next version.'})
    finally:module.publish=original
    memory=NativeMemory(fixture.root)
    journal_before_recovery=memory.transaction.journal.exists()
    with memory._transaction() as connection:operations=[dict(row) for row in connection.execute('SELECT * FROM operations')]
    result={'http_status':response.status_code,'http_body':response.text,'publications':publications,
        'initial':{k:v.decode() for k,v in initial.items()},'final_files':{p.name:p.read_text() for p in directory.iterdir()},
        'journal_before_recovery':journal_before_recovery,'journal_after_recovery':memory.transaction.journal.exists(),
        'operations':operations}
    print(json.dumps(result,indent=2))
    assert response.status_code==503,result
    assert (directory/'LATEST').read_text()=='3.2.2\n',result
    assert (directory/'v3.2.2.md').exists(),result
    assert not journal_before_recovery,result
finally:fixture.doCleanups()
