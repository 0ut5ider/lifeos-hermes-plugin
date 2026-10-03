# ABOUTME: Measures native diagnostic projection limits with synthetic owner records.
# ABOUTME: Preserves real native proposal receipts and actual CLI/RPC outcomes.
from dataclasses import replace
from pathlib import Path
import json, shutil, traceback, os, subprocess, sys
from test_memory_diagnostics import MemoryDiagnosticTests
from test_memory_native import OWNER, SOURCE
from lifeos_hook_bridge.memory_service import MemoryService

case=MemoryDiagnosticTests(); case.setUp()
try:
    memory=case.fixture.fixture.memory
    tools=case.root/'LIFEOS/TOOLS';tools.unlink();shutil.copytree(SOURCE/'LIFEOS/TOOLS',tools)
    (case.root/'LIFEOS/USER/PROJECTS.md').write_text('| **SyntheticLab** | synthetic |\n')
    target=case.root/'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md';target.write_text('# Synthetic rules\n')
    service=MemoryService(case.fixture.configuration)
    path=case.obs/'pending-proposals.jsonl'
    scope=replace(OWNER, proposals=('create','review','approve'))
    for name,edit in [('long', 'Synthetic long authorized proposal marker. '+ 'abcd '*8000),('escaped', 'Synthetic escaping control. '+ '\\'*5000)]:
        item={'type':'proposal','target_kind':'operational-rule','target_file':str(target),'edit':edit,'confidence':0.5,'rationale':'Synthetic owner control.'}
        saved=memory.native_add(scope,item,request_id='probe-'+name,project='',source_session='synthetic')
        print(json.dumps({'case':name,'receipt':saved,'edit_chars':len(edit)}),flush=True)
        assert saved['ok'] and saved['receipt']['status']=='pending',saved
        row=json.loads(path.read_text().splitlines()[-1])
        if name=='long':
            projection=service.native(case.fixture.context,'read_diagnostic',{'path':str(path)})
            managed=case.call('MemoryInsights.ts')
            print(json.dumps({'case':'long-diagnostic','projection':projection,'stdout':managed.stdout,'exit':managed.returncode}),flush=True)
        else:
            path.write_text((json.dumps(row)+'\n')*230)
            projection=service.native(case.fixture.context,'read_diagnostic',{'path':str(path)})
            managed=case.call('MemoryInsights.ts')
            print(json.dumps({'case':'escaped-volume','service_ok':projection.get('ok'),'projected_bytes':len(projection.get('content','').encode()),'wire_bytes':len(json.dumps(projection).encode()),'stdout':managed.stdout,'exit':managed.returncode}),flush=True)
    path.unlink()
    case.write('reviewer-runs.jsonl',[case.reviewer(duration_ms=10**400)])
    try:
        result=service.native(case.fixture.context,'read_diagnostic',{'path':str(case.obs/'reviewer-runs.jsonl')})
        print(json.dumps({'case':'large-number','result':result}),flush=True)
    except Exception as e:
        print(json.dumps({'case':'large-number','exception':type(e).__name__,'message':str(e)}),flush=True)
        traceback.print_exc()
    print(json.dumps({'case':'large-number-native','stdout':case.call('MemoryStatus.ts','--json').stdout}),flush=True)
finally:
    case.doCleanups()
