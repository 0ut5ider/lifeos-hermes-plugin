# ABOUTME: Isolates the snapshot byte cap from graph field and source caps.
# ABOUTME: Tests long synthetic Gear labels through the actual admitted native owner operation.
from pathlib import Path
import json,hashlib,base64
from test_memory_atlas_sync import MemoryAtlasSyncTests
out=Path(__file__).resolve().parent
f=MemoryAtlasSyncTests();f.setUp();rows=[]
try:
    (f.root/'LIFEOS/USER/PROJECTS.md').write_text('# Projects\n')
    for padding in [4600,4800,4900,5000]:
        text='## Computing\n'+''.join('| **Device '+str(i)+'** | Synthetic Machine '+str(i)+' '+('x'*padding)+' | daily |\n' for i in range(50))
        (f.root/'LIFEOS/USER/GEAR.md').write_text(text)
        m=f.owner.fixture.memory;collector=m._native('atlas_collect',collector='gear',content=text)
        plan=m._native('atlas_sync_plan',database=None,runs=[{'collector':'gear','scope':'full','result':collector},{'collector':'projects','scope':'full','result':{'complete':True,'assets':[],'edges':[]}}])
        paths=[f.graph(),f.graph().with_name('snapshot.json'),f.cache]
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}
        result=f.sync()
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}
        if padding==4600:assert result['ok'],result
        if padding==5000:assert not result['ok'] and before==after
        rows.append({'padding_bytes_per_name':padding,'source_bytes':len(text.encode()),'planned_database_bytes':len(base64.b64decode(plan['database'])),'planned_snapshot_python_bytes':len(json.dumps(plan['snapshot'],ensure_ascii=False).encode()),'result':result,'artifacts_preserved':before==after,'before':before,'after':after,'journal_present':m.transaction.journal.exists()})
    (out/'snapshot-byte-measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
finally:f.doCleanups()
