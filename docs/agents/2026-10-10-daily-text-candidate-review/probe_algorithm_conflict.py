# ABOUTME: Reproduces a concurrent Algorithm source edit after actual native publication.
# ABOUTME: Records transaction receipts and persisted artifacts in a disposable fixture.
import json, shutil
from pathlib import Path
from test_memory_native import NativeMemoryTests, SOURCE, OWNER
from lifeos_hook_bridge import memory_algorithm_edit as edits
fixture=NativeMemoryTests()
fixture.setUp()
try:
    root=fixture.root
    (root/'LIFEOS/PULSE').symlink_to(SOURCE/'LIFEOS/PULSE')
    hooks=root/'hooks'
    hooks.unlink();shutil.copytree(SOURCE/'hooks',hooks)
    directory=root/'LIFEOS/ALGORITHM'
    directory.mkdir()
    initial={'LATEST':'3.2.1\n','v3.2.1.md':'# The Algorithm 3.2.1\n\nSynthetic original doctrine.\n','changelog.md':'# Synthetic history\n'}
    for name,text in initial.items():(directory/name).write_text(text)
    original=edits.publish
    observed=[]
    def concurrent(path,data):
        original(path,data)
        if Path(path).is_relative_to(root):observed.append(str(Path(path).relative_to(root)))
        if Path(path)==directory/'LATEST':
            (directory/'v3.2.1.md').write_text('Synthetic later owner edit to the prior source.\n')
    edits.publish=concurrent
    try:
        try:
            result=edits.edit(fixture.memory,OWNER,'/api/algorithm-tab/doctrine',
                {'content':'# The Algorithm 3.2.1\n\n'+'Synthetic requested next doctrine. '*30,'bump':'patch','note':'Synthetic requested version.'},check_current=lambda:None)
        except Exception as error:result={'exception':type(error).__name__,'message':str(error)}
    finally:edits.publish=original
    with fixture.memory._transaction() as connection:
        operations=[dict(row) for row in connection.execute('SELECT * FROM operations')]
    outcome={'result':result,'observed_publications':observed,'files':{p.name:p.read_text() for p in directory.iterdir()},
        'journal_exists':fixture.memory.transaction.journal.exists(),'operations':operations}
    print(json.dumps(outcome,indent=2))
    assert result.get('exception')=='MemoryUnavailable',outcome
    assert (directory/'LATEST').read_text()=='3.2.2\n',outcome
    assert (directory/'v3.2.2.md').exists(),outcome
    assert any(json.loads(row['receipt'])['status']=='conflict' for row in operations),outcome
    assert not fixture.memory.transaction.journal.exists(),outcome
finally:fixture.doCleanups()
