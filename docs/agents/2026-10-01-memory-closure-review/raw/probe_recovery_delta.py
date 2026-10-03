# ABOUTME: Observes a real native hot publication interrupted before registry commit.
# ABOUTME: Compares recovered authoritative facts with the registered delta composer output.
import json
import os
from pathlib import Path
import subprocess
import sys
import test_memory_delta as delta
from test_memory_native import OWNER

out = Path(__file__).parent
result = []
for interrupted in (False, True):
    f = delta.MemoryDeltaTests()
    f.setUp()
    try:
        baseline = f.remember('Synthetic committed recovery control', 'baseline')
        marker = 'Synthetic aborted recovery candidate'
        if interrupted:
            script = '''import os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from test_memory_native import OWNER
memory = NativeMemory(Path(sys.argv[1]))
def interrupt(*args, **kwargs):
    os._exit(73)
memory._record = interrupt
memory.remember(OWNER, category='principal', content='RULE: Synthetic aborted recovery candidate',
    title='', project='', request_id='interrupted-save')
'''
            child = subprocess.run([sys.executable, '-c', script, str(f.root)], capture_output=True, text=True)
            assert child.returncode == 73, child.stderr
            before_recovery = (f.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md').read_text()
            assert marker in before_recovery
        else:
            saved = f.remember(marker, 'successful-save')
            assert saved['status'] == 'committed', saved
            child = None
        # This real governed read completes journal recovery before the composer runs.
        hot = f.memory.read_hot(OWNER, 'principal')
        recalled = f.memory.recall(OWNER, 'recovery')
        log = (f.obs / 'memory-writes.jsonl').read_text()
        output = f.call()
        result.append({'interrupted': interrupted, 'exit': child.returncode if child else None,
            'current_hot': hot, 'ordinary_recall': recalled, 'log': log, 'registered_output': output,
            'aborted_marker_in_current': marker in json.dumps(recalled),
            'aborted_marker_in_output': marker in output})
    finally:
        f.doCleanups()
(out / 'recovery-delta-results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
