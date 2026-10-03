# ABOUTME: Measures governed fixture divergence through native restore and PULSE edit.
# ABOUTME: Tests real public functions and private local files without model requests.
import json,os,subprocess,hashlib
from dataclasses import asdict
from test_memory_delegation import MemoryDelegationTests
from test_memory_native import SOURCE,OWNER
f=MemoryDelegationTests();f.setUp()
try:
    retired='RULE: synthetic audit retired puffin marker'
    old=f.fixture.remember(retired,'retire','principal')
    f.fixture.memory.forget(OWNER,old['reference'],'forget')
    live=f.fixture.remember('RULE: synthetic audit live heron marker','live','principal')
    def current_reference():
        try:return f.fixture.memory.get(OWNER,live['reference'])
        except Exception as e:return {'exception':type(e).__name__,'message':str(e)}
    path=f.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
    base=dict(os.environ,HOME=str(f.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
    base.pop('LIFEOS_MEMORY_INTERNAL',None);base.pop('LIFEOS_MEMORY_CONTEXT',None)
    def run(label,args,ctx=False):
        env=dict(base)
        if ctx:env['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(f.context))
        p=subprocess.run([f.fixture.memory.bun,'--no-install',*args],text=True,capture_output=True,cwd=f.root,env=env,timeout=45)
        print(json.dumps({'case':label,'argv':args,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
    snaps=list((f.root/'LIFEOS/MEMORY/OBSERVABILITY/memory-snapshots').glob('*.md'))
    snap=next(s for s in snaps if retired in s.read_text())
    before=path.read_text()
    run('restore_without_context',[str(SOURCE/'LIFEOS/TOOLS/MemoryRestore.ts'),'restore',snap.name])
    print(json.dumps({'case':'restore_bytes_and_registry','retired_restored':retired in path.read_text(),'live_removed':'heron' not in path.read_text(),'current_reference':current_reference()}))
    # Reset only private fixture bytes for a separate real edit path probe.
    path.write_text(before)
    req={'pageId':'synthetic','sourceFile':'USER/PRINCIPAL/PRINCIPAL_MEMORY.md','fieldPath':'body','beforeHash':hashlib.sha256(before.encode()).hexdigest(),'newContent':'<!-- BEGIN ENTRIES -->\n'+retired+'\n<!-- END ENTRIES -->\n','draftStartedAt':'2099-01-01T00:00:00Z'}
    run('pulse_edit_without_context',['-e',f'const m=await import({json.dumps(str(SOURCE/"LIFEOS/PULSE/edit/edit-handler.ts"))}); console.log(JSON.stringify(m.applyEdit({json.dumps(req)})));'])
    print(json.dumps({'case':'edit_bytes_and_registry','retired_restored':retired in path.read_text(),'current_reference':current_reference()}))
    path.write_text(before)
    identity=f.root/'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md';identity.write_text('Synthetic private identity osprey marker')
    for rel in ['DIGITAL_ASSISTANT/DA_IDENTITY.md','TELOS/PRINCIPAL_TELOS.md','PROJECTS.md']:
        p=f.root/'LIFEOS/USER'/rel;p.parent.mkdir(exist_ok=True,parents=True);p.write_text('Synthetic context fixture')
    source=str(SOURCE/'LIFEOS/PULSE/lib/lifeos-context.ts')
    run('context_missing_caller',['-e',f'const m=await import({json.dumps(source)}); console.log(JSON.stringify({{block:await m.buildLifeosContextBlock("audit")}}));'])
    run('context_cache_revoke',['-e',f'const m=await import({json.dumps(source)}); const first=await m.buildLifeosContextBlock(); delete process.env.LIFEOS_MEMORY_CONTEXT; const second=await m.buildLifeosContextBlock(); console.log(JSON.stringify({{first,second,identical:first===second}}));'],True)
finally:f.doCleanups()
