# ABOUTME: Measures current-registry delta projection at both native hot-file caps.
# ABOUTME: Publishes actual native entries, adopts them, and times the registered composer.
import json
from pathlib import Path
import time
import test_memory_delta as delta
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import HOT_FILES
out = Path(__file__).parent
result=[]
for entries_per_file in (1, 48):
    f=delta.MemoryDeltaTests();f.setUp()
    try:
        for category in ('principal', 'assistant'):
            entries=[f'RULE: Synthetic current {category} fact number {n}' for n in range(entries_per_file)]
            saved=f.memory._native('set_hot',path=str(f.root/HOT_FILES[category]),entries=entries,
                writer='MemorySystem.add',allowDrastic=False)
            assert saved['ok'], saved
        preview=f.memory.preview_adoption(OWNER)
        adopted=f.memory.adopt(OWNER,preview['signature'],{},'adopt-cap')
        assert adopted['status']=='committed', adopted
        start=time.monotonic()
        output=f.call(timeout=45)
        elapsed=time.monotonic()-start
        result.append({'entries_per_file':entries_per_file,'current_records':len(preview['records']),
            'seconds':elapsed,'within_8_seconds':elapsed<8,'output':output})
    finally:f.doCleanups()
(out/'distinct-delta-latency-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
