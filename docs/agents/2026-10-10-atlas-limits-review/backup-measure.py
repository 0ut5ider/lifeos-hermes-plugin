# ABOUTME: Measures actual native backup omission and a retained synthetic Atlas rebuild.
# ABOUTME: Verifies current derived assets while preserving original graph and snapshot bytes.
from pathlib import Path
from contextlib import closing
from dataclasses import asdict
import os, json, subprocess, sqlite3, hashlib
from test_memory_atlas_sync import MemoryAtlasSyncTests
from test_memory_atlas_insight import MemoryAtlasInsightTests
from lifeos_hook_bridge.memory_backup import create,inspect
from lifeos_hook_bridge.memory_backup_recovery import recover
from test_memory_native import OWNER
out=Path(__file__).resolve().parent
f=MemoryAtlasSyncTests();f.setUp()
try:
    f.sources();assert f.sync()['ok'];p=MemoryAtlasInsightTests.prepare(f);assert f.call('atlas_insight_publish',signature=p['signature'],value=MemoryAtlasInsightTests.value(f,p))['ok']
    home=f.root.parent; memory=f.owner.fixture.memory
    paths=[f.graph(),f.graph().with_name('snapshot.json'),f.cache]
    originals={p.name:p.read_bytes() for p in paths}
    result=create(memory,OWNER,home/'backup');manifest=inspect(memory,OWNER,home/'backup',result['signature'])
    names=[r['path'] for r in manifest['files']]
    restored=recover(memory,OWNER,home/'backup',result['signature'],home/'recovery')
    restoredhome=Path(restored['root']).parent
    assert not (restoredhome/'.local/state/lifeos/atlas/atlas.db').exists()
    assert not (restoredhome/'.local/state/lifeos/atlas/snapshot.json').exists()
    assert 'MEMORY/STATE/atlas-insights.json' in names
    assert (restoredhome/'.config/LIFEOS/USER/MEMORY/STATE/atlas-insights.json').read_bytes()==originals[f.cache.name]
    # Retain exact prior state, then exercise managed rebuild from retained sources.
    retained=home/'atlas-retained';retained.mkdir(mode=0o700)
    with memory._transaction():pass
    for path in paths:path.rename(retained/path.name)
    rebuilt=f.sync();assert rebuilt['ok'],rebuilt
    with closing(sqlite3.connect(f.graph())) as c:
        current=c.execute('SELECT canonical_key FROM asset ORDER BY canonical_key').fetchall()
        runs=c.execute('SELECT COUNT(*) FROM sync_run').fetchone()[0]
    for name,data in originals.items():assert (retained/name).read_bytes()==data
    # Restore the retained bytes as a group while the synthetic fixture has no writer.
    for path in paths:
        if path.exists():path.rename(home/('rebuilt-'+path.name))
        (retained/path.name).rename(path)
    assert {p.name:p.read_bytes() for p in paths}==originals
    record={'native_backup':result,'manifest_files':names,'recovery':{'status':restored['status'],'atlas_db_present':False,'atlas_snapshot_present':False,'narrative_bytes_retained':True},'retained_rebuild':{'result':rebuilt,'current_keys':current,'runs':runs,'all_prior_bytes_retained':True,'exact_group_return':True},'state_location_relative_to_home':'.local/state/lifeos/atlas','artifacts_sha256':{n:hashlib.sha256(d).hexdigest() for n,d in originals.items()}}
    # Omit temporary absolute fixture paths from retained record.
    record['native_backup'].pop('snapshot',None)
    (out/'backup-measurements.json').write_text(json.dumps(record,indent=2)+'\n')
finally:f.doCleanups()
