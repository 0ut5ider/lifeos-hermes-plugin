# ABOUTME: Exercises real managed Atlas boundaries in disposable synthetic owner stores.
# ABOUTME: Records exact artifact preservation, freshness, and publication recovery results.
from pathlib import Path
import os, sys, json, subprocess, sqlite3, hashlib, base64
from contextlib import closing
from dataclasses import asdict
from test_memory_atlas_sync import MemoryAtlasSyncTests
from test_memory_atlas_insight import MemoryAtlasInsightTests
from lifeos_hook_bridge import memory_atlas_sync

OUT=Path(__file__).resolve().parent
records=[]
def gear(n):return '## Computing\n'+''.join(f'| **Device {i}** | Synthetic Machine 0-{i} | daily |\n' for i in range(n))
def projects(n):return '| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'+''.join(f'| Synthetic Project 0-{i} | /synthetic/project-{i} github.com/synthetic/repo-0-{i} | app-0-{i}.example.invalid | local |\n' for i in range(n))
def sizes(f):
    paths=[f.graph(),f.graph().with_name('snapshot.json'),f.cache]
    return {p.name:{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(p.stat().st_mode&0o777)} for p in paths if p.exists()}
def rows(f):
    with closing(sqlite3.connect(f.graph())) as c:return {t:c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['asset','edge','source_observation','edge_observation','sync_run','lifecycle_event']}
def native_seed(f,runs):
    module=f.root/'LIFEOS/ATLAS/Store.ts'
    script='import {Store} from '+json.dumps(str(module))+';const s=new Store();for(let i=0;i<'+str(runs)+';i++)s.applyRun("gear","full",{complete:false,assets:[],edges:[]});s.db.exec("PRAGMA wal_checkpoint(TRUNCATE)");s.db.exec("PRAGMA journal_mode=DELETE");s.close();'
    p=subprocess.run(['bun','--no-install','-e',script],env=dict(os.environ,HOME=str(f.root.parent),LIFEOS_MEMORY_INTERNAL='1'),capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr

def fixture(g=50,p=20):
    f=MemoryAtlasSyncTests();f.setUp()
    (f.root/'LIFEOS/USER/GEAR.md').write_text(gear(g));(f.root/'LIFEOS/USER/PROJECTS.md').write_text(projects(p));return f

def record(name,**values):
    records.append({'name':name,**values});(OUT/'managed-measurements.json').write_text(json.dumps(records,indent=2)+'\n');print(name,flush=True)

f=fixture()
try:
    assert f.sync()['ok']; prepared=MemoryAtlasInsightTests.prepare(f);assert f.call('atlas_insight_publish',signature=prepared['signature'],value=MemoryAtlasInsightTests.value(f,prepared))['ok']
    native_seed(f,398)
    before=sizes(f)
    near=f.sync();assert near['ok'],near
    assert rows(f)['sync_run']==402
    before=sizes(f)
    from lifeos_hook_bridge.memory_atlas import view
    scope=f.service.scope(f.owner.context)
    before_view=view(f.owner.fixture.memory,scope,target='/api/atlas/insights')
    assert before_view['status']==200
    result=f.sync(); journal=f.owner.fixture.memory.transaction.journal
    journal_size=journal.stat().st_size if journal.exists() else None
    after=sizes(f);run_rows=rows(f)
    with f.owner.fixture.memory._transaction():pass
    recovered=sizes(f)
    assert recovered==before
    record('projection-history-limit',near_result=near,before=before,result=result,after_publication=after,rows_after_publication=run_rows,journal_bytes=journal_size,recovered=recovered,exact_recovery=True,rows_recovered=rows(f),view_before_status=before_view['status'],view_after_recovery_status=view(f.owner.fixture.memory,scope,target='/api/atlas/insights')['status'])
finally:f.doCleanups()

for g,p in [(100,50),(100,100),(300,150),(0,80),(0,85),(0,100)]:
    f=fixture(g,p)
    try:
        result=f.sync(); artifacts=sizes(f); journal=f.owner.fixture.memory.transaction.journal; journal_bytes=journal.stat().st_size if journal.exists() else None; count=rows(f) if f.graph().exists() else None
        with f.owner.fixture.memory._transaction():pass
        record(f'inventory-{g}-{p}',result=result,artifacts_after_operation=artifacts,rows_after_operation=count,journal_bytes=journal_bytes,artifacts_after_recovery=sizes(f),source_bytes={'gear':len(gear(g).encode()),'projects':len(projects(p).encode())})
    finally:f.doCleanups()

f=fixture()
try:
    assert f.sync()['ok']; prepared=MemoryAtlasInsightTests.prepare(f);assert f.call('atlas_insight_publish',signature=prepared['signature'],value=MemoryAtlasInsightTests.value(f,prepared))['ok']
    original=sizes(f)
    (f.root/'LIFEOS/USER/PROJECTS.md').write_text(projects(20).replace('local','changed-deploy'))
    # Actual admitted service reads with source changes, without a sync.
    from lifeos_hook_bridge.memory_atlas import view
    scope=f.service.scope(f.owner.context)
    before_source_view=view(f.owner.fixture.memory,scope,target='/api/atlas/insights')
    assert before_source_view['body']['stale'] is False
    changed=f.call('atlas_insight_prepare');assert changed['ok'],changed
    assert changed['plan']['hash']==prepared['plan']['hash']
    assert sizes(f)==original
    # Over-size planned snapshot must preserve every current graph/cache artifact.
    (f.root/'LIFEOS/USER/GEAR.md').write_text(gear(300));(f.root/'LIFEOS/USER/PROJECTS.md').write_text(projects(150))
    refusal=f.sync();assert not refusal['ok'],refusal;assert sizes(f)==original
    record('snapshot-plan-refusal',result=refusal,before=original,after=sizes(f),journal_exists=f.owner.fixture.memory.transaction.journal.exists(),changed_source_prepare_hash_matches_prior=True,changed_source_insight_stale=before_source_view['body']['stale'])
    (f.root/'LIFEOS/USER/GEAR.md').write_text(gear(50));(f.root/'LIFEOS/USER/PROJECTS.md').write_text(projects(20))
    # Source exact and over bounds with comments that add no graph assets.
    path=f.root/'LIFEOS/USER/GEAR.md';source=gear(50)
    for n in [262144,262145]:
        path.write_text(source+'x'*(n-len(source.encode())))
        before=sizes(f);result=f.sync();record('source-'+str(n),result=result,before=before,after=sizes(f),bytes_preserved=before==sizes(f))
    path.write_text(source)
    # Actual database exact/over bound using valid SQLite plus harmless trailing zero bytes.
    for n in [2097152,2097153]:
        original_database=f.graph().read_bytes();f.graph().write_bytes(original_database+b'\0'*(n-len(original_database)))
        before=sizes(f);result=f.sync();record('database-'+str(n),result=result,before=before,after=sizes(f),bytes_preserved=before==sizes(f))
        f.graph().write_bytes(original_database)
finally:f.doCleanups()

# Re-run actual interruption and later edit recovery controls independently.
for name in ['test_process_death_and_post_publication_changes_keep_recovery','test_later_edits_preserve_the_whole_publication_group_and_recovery']:
    f=MemoryAtlasSyncTests(name);f.setUp()
    try:getattr(f,name)();record(name,passed=True)
    finally:f.doCleanups()
(OUT/'managed.done').touch()
