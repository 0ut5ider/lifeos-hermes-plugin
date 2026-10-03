# ABOUTME: Tests private filename admission through native adoption and canonical views.
# ABOUTME: Uses public native tools and synthetic source text in a disposable fixture.
import json, pathlib
from test_memory_native import NativeMemoryTests, OWNER
from lifeos_hook_bridge.memory_canonical import corpus
from lifeos_hook_bridge.memory_knowledge import view
fixture=NativeMemoryTests(); fixture.temporary_parent=str(pathlib.Path(__file__).parent/'fixture-home/tmp'); fixture.setUp()
try:
    marker='SYNTHETIC_PRIVATE_FILENAME_MARKER'
    relative='LIFEOS/MEMORY/KNOWLEDGE/Research/<private>'+marker+'.md'
    path=fixture.root/relative
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('---\ntitle: Safe Synthetic Note\ntype: research\ncreated: 2026-10-02T00:00:00Z\nupdated: 2026-10-02T00:00:00Z\n---\n\nSafeSyntheticCurrentBody\n')
    (fixture.root/'LIFEOS/PULSE').symlink_to(pathlib.Path(__import__('os').environ['LIFEOS_MEMORY_SOURCE'])/'LIFEOS/PULSE')
    validation=fixture.memory._native('validate_source_batch',contents=[str(path)])
    preview=fixture.memory.preview_adoption(OWNER)
    adopted=fixture.memory.adopt(OWNER,preview['signature'],{relative:'lab'},'adopt-private-filename')
    result=corpus(fixture.memory,OWNER,str(fixture.root/'LIFEOS/MEMORY'))
    knowledge=view(fixture.memory,OWNER,'/api/knowledge')
    print(json.dumps({'label_validation':validation,'preview':preview,'adopted':adopted,'canonical':result,'knowledge':knowledge,'private_marker_in_canonical':marker in json.dumps(result),'private_marker_in_knowledge':marker in json.dumps(knowledge)},indent=2))
finally:
    fixture.doCleanups()
