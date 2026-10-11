# ABOUTME: Repeats the reviewer's native cases under the primary agent's verification.
# ABOUTME: Records commands, output, unchanged source hashes, and durable completion.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

out = Path(__file__).parent
repo = out.parents[3]
native = '/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install'
hermes = '/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-11577ed4/hermes'
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
    PYTHONPATH=f'{repo}:{repo}/tests:{hermes}', LIFEOS_HERMES_SOURCE=hermes,
    LIFEOS_MEMORY_SOURCE=native, LIFEOS_TASK_HOOK_PATH=native+'/hooks/TaskGovernance.hook.ts')
additional = out/'additional-cases.py'
shutil.copyfile(out.parent/'additional-cases.py', additional)
paths = [*repo.glob('lifeos_hook_bridge/memory_atlas*.py'), repo/'lifeos_hook_bridge/memory_access.py',
    repo/'lifeos_hook_bridge/memory_service.py', repo/'lifeos_hook_bridge/cli.py',
    repo/'tests/test_memory_atlas_retention.py', repo/'tests/test_memory_atlas_capacity.py']
hashes = {str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
commands = {
    'focused': [sys.executable, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v',
        'test_memory_atlas_retention', 'test_memory_atlas_capacity.MemoryAtlasCapacityTests'],
    'additional': [sys.executable, '-W', 'error::ResourceWarning', str(additional), 'AdditionalCases'],
}
records = {}
for label, command in commands.items():
    started = time.monotonic()
    result = subprocess.run(command, cwd=repo, env=environment, capture_output=True, text=True)
    (out/(label+'.stdout')).write_text(result.stdout)
    (out/(label+'.stderr')).write_text(result.stderr)
    records[label] = {'command':command, 'exit_code':result.returncode,
        'duration_seconds':time.monotonic()-started}
unchanged = all(hashlib.sha256((repo/path).read_bytes()).hexdigest()==value for path,value in hashes.items())
record = {'review_head':'72b0d4a2', 'results':records, 'source_hashes':hashes,
    'source_hashes_unchanged':unchanged,
    'exit_code':0 if unchanged and all(r['exit_code']==0 for r in records.values()) else 1}
(out/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'verification.done').write_text(str(record['exit_code'])+'\n')
