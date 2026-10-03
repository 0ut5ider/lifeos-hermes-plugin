# ABOUTME: Measures actual native hot reads during registered full-cap recall.
# ABOUTME: Instruments only a synthetic RPC connector and preserves native request behavior.
from collections import Counter
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import test_memory_delta as delta
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import HOT_FILES
out=Path(__file__).resolve().parent
f=delta.MemoryDeltaTests();f.setUp()
try:
    for category in ('principal','assistant'):
        entries=[f'RULE: Synthetic instrumented {category} fact {number}' for number in range(48)]
        saved=f.memory._native('set_hot',path=str(f.root/HOT_FILES[category]),entries=entries,
            writer='MemorySystem.add',allowDrastic=False)
        assert saved['ok'],saved
    preview=f.memory.preview_adoption(OWNER)
    assert f.memory.adopt(OWNER,preview['signature'],{},'instrumented-adoption')['status']=='committed'
    connector=f.root/'LIFEOS/USER/CONFIG/memory-access.json'
    content=json.loads(connector.read_text())
    content['command']=[sys.executable,str(out/'instrument_native_rpc.py'),'--configuration',str(f.fixture.configuration.path)]
    connector.write_text(json.dumps(content));connector.chmod(0o600)
    log=f.fixture.fixture.home/'native-calls.jsonl'
    environment=dict(os.environ, HOME=str(f.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1',
        LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(f.fixture.context)), LIFEOS_REVIEW_PROJECT=str(Path.cwd()),
        LIFEOS_REVIEW_CALL_LOG=str(log))
    for key in ('LIFEOS_MEMORY_INTERNAL','CLAUDE_AGENT_TYPE','CLAUDE_CODE_SUBAGENT_NAME',
        'CLAUDE_CODE_SUBAGENT_TYPE','CLAUDE_CODE_FORK_SUBAGENT','CLAUDE_AGENT_SDK','CLAUDE_PROJECT_DIR'):
        environment.pop(key,None)
    started=time.monotonic()
    completed=subprocess.run(['bun','--no-install',str(f.root/'hooks/MemoryTurnStart.hook.ts')],
        input=json.dumps({'session_id':'instrumented-session','prompt':'memory'}),env=environment,cwd=f.root,
        capture_output=True,text=True,timeout=45)
    elapsed=time.monotonic()-started
    assert completed.returncode==0 and not completed.stderr,(completed.returncode,completed.stderr)
    rows=[json.loads(line) for line in log.read_text().splitlines()]
    result={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'seconds':elapsed,'counts':dict(Counter((r['operation']+'/'+r['action']) for r in rows)),
        'read_hot_seconds':sum(r['seconds'] for r in rows if r['action']=='read_hot'),
        'calls':rows,'registered_output':completed.stdout}
    (out/'corpus-instrumentation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('source_head','seconds','counts','read_hot_seconds')},indent=2))
finally:f.doCleanups()
