# ABOUTME: Probes public native read paths against disposable governed records.
# ABOUTME: Preserves exact subprocess outputs without contacting external services.
import json, os, subprocess
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict
from test_memory_delegation import MemoryDelegationTests
from test_memory_native import OWNER, SOURCE

f=MemoryDelegationTests(); f.setUp()
try:
    marker='RULE: synthetic audit private cormorant marker'
    saved=f.fixture.remember(marker, 'audit-private', 'principal')
    forgotten=f.fixture.memory.forget(OWNER,saved['reference'],'audit-forget')
    current=f.fixture.remember('RULE: synthetic audit current pelican marker','audit-current','principal')
    base=dict(os.environ,HOME=str(f.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
    for key in ['LIFEOS_MEMORY_INTERNAL','LIFEOS_MEMORY_CONTEXT','CLAUDE_AGENT_TYPE','CLAUDE_CODE_SUBAGENT_NAME','CLAUDE_CODE_SUBAGENT_TYPE','CLAUDE_CODE_FORK_SUBAGENT','CLAUDE_AGENT_SDK','CLAUDE_PROJECT_DIR']:
        base.pop(key,None)
    def call(label,args,context=False,stdin=''):
        env=dict(base)
        if context: env['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(f.context))
        p=subprocess.run([f.fixture.memory.bun,'--no-install',*args],input=stdin,text=True,capture_output=True,env=env,cwd=f.root,timeout=45)
        value={'case':label,'argv':args,'owner_context':context,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        print(json.dumps(value))
        return value
    print(json.dumps({'case':'native_receipts','saved':saved,'forgotten':forgotten,'current':current}))
    obs=f.root/'LIFEOS/MEMORY/OBSERVABILITY'
    print(json.dumps({'case':'actual_native_write_log','body':(obs/'memory-writes.jsonl').read_text()}))
    for ctx in (False, True):
        cursor=obs/'memory-delta-cursor.json'
        if cursor.exists(): cursor.unlink()
        call('turn_start_retired_delta', [str(SOURCE/'hooks/MemoryTurnStart.hook.ts')],ctx,json.dumps({'session_id':'audit','prompt':'cormorant'}))
    call('pulse_missing_context',['-e',f'const m=await import({json.dumps(str(SOURCE/"LIFEOS/PULSE/modules/memory.ts"))}); const r=await m.handleRequest(new Request("http://localhost/api/memory"),"/api/memory"); console.log(await r.text());'])
    # Native-shaped retained proposal and failed reviewer diagnostics in disposable observability.
    ts=datetime.now(timezone.utc).isoformat()
    (obs/'pending-proposals.jsonl').write_text(json.dumps({'id':'audit-proposal','ts':ts,'created_at':ts,'status':'rejected','target_file':'PRINCIPAL/TELOS.md','edit':marker})+'\n')
    (obs/'reviewer-runs.jsonl').write_text(json.dumps({'ts':ts,'ok':False,'error':marker})+'\n')
    call('insights_retired_proposal',[str(SOURCE/'LIFEOS/TOOLS/MemoryInsights.ts')])
    call('status_retained_error',[str(SOURCE/'LIFEOS/TOOLS/MemoryStatus.ts'),'--json'])
    knowledge=f.root/'LIFEOS/MEMORY/KNOWLEDGE/Research'; knowledge.mkdir(parents=True,exist_ok=True)
    (knowledge/'audit.md').write_text('---\nid: audit-retained\ntitle: Synthetic historical note\ncreated: 2026-01-01T00:00:00Z\n---\n'+marker+'\n')
    call('cortex_get_retired',[str(SOURCE/'LIFEOS/TOOLS/Cortex.ts'),'get','audit-retained'])
    # Invalid connector also must not permit fallback.
    connector=f.root/'LIFEOS/USER/CONFIG/memory-access.json'; connector.write_text('{invalid')
    call('pulse_invalid_connector',['-e',f'const m=await import({json.dumps(str(SOURCE/"LIFEOS/PULSE/modules/memory.ts"))}); const r=await m.handleRequest(new Request("http://localhost/api/memory"),"/api/memory"); console.log(await r.text());'])
    call('cortex_invalid_connector',[str(SOURCE/'LIFEOS/TOOLS/Cortex.ts'),'get','audit-retained'])
finally:
    f.doCleanups()
