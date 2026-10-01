# ABOUTME: Tests audit-log capture during native hot publication in disposable subclasses.
# ABOUTME: Leaves implementation unchanged and measures real interruption and recovery outputs.
import json
from pathlib import Path
import subprocess
import sys
import test_memory_delta as delta
from test_memory_native import OWNER

out = Path(__file__).parent
results = []
for category in ('principal', 'assistant'):
    for mode in ('remember', 'native_add'):
        for journal_log in (False, True):
            f = delta.MemoryDeltaTests()
            f.setUp()
            try:
                baseline = f.fixture.fixture.remember('RULE: Synthetic committed audit prefix', 'baseline', category)
                logpath = f.obs / 'memory-writes.jsonl'
                prefix = logpath.read_bytes()
                script = '''import os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from test_memory_native import OWNER
class AuditJournalMemory(NativeMemory):
    def _publication_paths(self, connection, scope, payload):
        paths = super()._publication_paths(connection, scope, payload)
        if sys.argv[4] == 'True':
            paths.append('LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl')
        return paths
memory = AuditJournalMemory(Path(sys.argv[1]))
memory._record = lambda *args, **kwargs: os._exit(73)
if sys.argv[3] == 'remember':
    memory.remember(OWNER, category=sys.argv[2], content='RULE: Synthetic interrupted audit candidate',
        title='', project='', request_id='interrupted')
else:
    memory.native_add(OWNER, {'type':'memory', 'actor':sys.argv[2],
        'content':'RULE: Synthetic interrupted audit candidate'}, request_id='interrupted', project='')
'''
                child = subprocess.run([sys.executable, '-c', script, str(f.root), category, mode, str(journal_log)],
                    capture_output=True, text=True, timeout=30)
                assert child.returncode == 73, child.stderr
                published_log = logpath.read_text()
                journal = json.loads(f.memory.transaction.journal.read_text())
                hot = f.memory.read_hot(OWNER, category)
                recovered_log = logpath.read_text()
                output = f.call()
                marker = 'Synthetic interrupted audit candidate'
                results.append({'category':category, 'mode':mode, 'journal_log':journal_log,
                    'child_exit':child.returncode, 'recovery_journal':journal,
                    'before_log':prefix.decode(), 'published_log':published_log, 'recovered_log':recovered_log,
                    'prefix_restored_exactly':prefix == logpath.read_bytes(), 'current_hot':hot,
                    'registered_output':output, 'candidate_current':marker in json.dumps(hot),
                    'candidate_surfaced':marker in output})
            finally:
                f.doCleanups()
(out / 'recovery-journal-hypothesis-results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps([{key:row[key] for key in ('category','mode','journal_log','child_exit',
    'prefix_restored_exactly','candidate_current','candidate_surfaced')} for row in results], indent=2))
assert all(not row['candidate_current'] for row in results)
assert all(row['prefix_restored_exactly'] and not row['candidate_surfaced']
    for row in results if row['journal_log'])
assert all(not row['prefix_restored_exactly'] and row['candidate_surfaced']
    for row in results if not row['journal_log'])
