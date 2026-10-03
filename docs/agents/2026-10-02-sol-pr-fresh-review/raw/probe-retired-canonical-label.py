# ABOUTME: Tests normalized retired filenames in governed canonical labels.
# ABOUTME: Uses an actual synthetic forget receipt and a safe adopted note body.
import json, pathlib, os
from datetime import datetime, timezone
from test_memory_native import NativeMemoryTests, OWNER
from lifeos_hook_bridge.memory_canonical import corpus
from lifeos_hook_bridge.memory_knowledge import view
OUT=pathlib.Path(__file__).resolve().parent
fixture=NativeMemoryTests();fixture.temporary_parent=str(OUT/'fixture-home/tmp');fixture.setUp()
try:
    claim='Synthetic retired canonical label'
    saved=fixture.remember('RULE: '+claim,'retired-label-save','principal')
    forgotten=fixture.memory.forget(OWNER,saved['reference'],'retired-label-forget')
    relative='LIFEOS/MEMORY/KNOWLEDGE/Research/'+claim.replace(' ','_')+'.md'
    path=fixture.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('---\ntitle: Safe Synthetic Note\ntype: research\ncreated: 2026-10-02T00:00:00Z\nupdated: 2026-10-02T00:00:00Z\n---\n\nSafeSyntheticCurrentBody\n')
    (fixture.root/'LIFEOS/PULSE').symlink_to(pathlib.Path(os.environ['LIFEOS_MEMORY_SOURCE'])/'LIFEOS/PULSE')
    preview=fixture.memory.preview_adoption(OWNER)
    adopted=fixture.memory.adopt(OWNER,preview['signature'],{relative:'lab'},'adopt-retired-label')
    result=corpus(fixture.memory,OWNER,str(fixture.root/'LIFEOS/MEMORY'))
    knowledge=view(fixture.memory,OWNER,'/api/knowledge')
    normalized=fixture.memory.filter_history(OWNER,relative.replace('_',' '),datetime.now(timezone.utc).isoformat())
    print(json.dumps({'forget':forgotten,'adopted':adopted,'canonical':result,'knowledge':knowledge,
        'normalized_label_excluded':normalized['excluded'],'retired_label_in_response':claim.replace(' ','_') in json.dumps(knowledge)},indent=2))
finally:fixture.doCleanups()
