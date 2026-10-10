# ABOUTME: Measures actual internal Atlas planning transport and near-limit recovery journal bytes.
# ABOUTME: Uses synthetic SQLite bytes and real native managed publication interruption.
from pathlib import Path
from dataclasses import asdict
import json,base64,subprocess,sys,hashlib
from test_memory_atlas_sync import MemoryAtlasSyncTests
out=Path(__file__).resolve().parent
f=MemoryAtlasSyncTests();f.setUp()
try:
    f.sources();assert f.sync()['ok'];m=f.owner.fixture.memory
    original=f.graph().read_bytes();f.graph().write_bytes(original+b'\0'*(2097152-len(original)))
    before={p.name:p.read_bytes() for p in [f.graph(),f.graph().with_name('snapshot.json')]}
    runs=[{'collector':name,'scope':'full','result':m._native('atlas_collect',collector=name,content=(f.root/relative).read_text())}for name,relative in [('gear','LIFEOS/USER/GEAR.md'),('projects','LIFEOS/USER/PROJECTS.md')]]
    args={'database':base64.b64encode(before['atlas.db']).decode(),'runs':runs}
    plan=m._native('atlas_sync_plan',**args)
    (out/'transport-native-plan.json').write_text(json.dumps(plan)+'\n')
    p=subprocess.run([sys.executable,str(Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests/memory_atlas_sync_process.py')),str(f.configuration.path),json.dumps(asdict(f.owner.context)),'interrupt'],capture_output=True,text=True,timeout=30)
    assert p.returncode==73 and p.stderr=='',(p.returncode,p.stderr)
    journal=m.transaction.journal.read_bytes()
    with m._transaction():pass
    assert {p.name:p.read_bytes() for p in [f.graph(),f.graph().with_name('snapshot.json')]}==before
    data={'database_input_bytes':len(before['atlas.db']),'database_base64_bytes':len(args['database']),'native_input_python_json_bytes':len(json.dumps({'action':'atlas_sync_plan',**args}).encode()),'native_plan_python_json_bytes':len(json.dumps(plan).encode()),'native_plan_compact_json_bytes':len(json.dumps(plan,separators=(',',':'),ensure_ascii=False).encode()),'database_planned_bytes':len(base64.b64decode(plan['database'])),'snapshot_python_json_bytes':len(json.dumps(plan['snapshot'],ensure_ascii=False).encode()),'publication_journal_bytes':len(journal),'interruption_exit_code':p.returncode,'recovery_exact':True,'recovered_database_sha256':hashlib.sha256(f.graph().read_bytes()).hexdigest()}
    (out/'transport-measurements.json').write_text(json.dumps(data,indent=2)+'\n')
finally:f.doCleanups()
