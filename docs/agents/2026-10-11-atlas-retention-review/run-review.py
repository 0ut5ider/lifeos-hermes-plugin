# ABOUTME: Runs focused review cases against real native sources in temporary fixtures.
# ABOUTME: Retains the command, output, source hashes, and completion marker.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
repo = Path(__file__).resolve().parents[3]
out = Path(__file__).parent
native = '/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install'
hermes = '/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-11577ed4/hermes'
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=f'{repo}:{repo}/tests:{hermes}', LIFEOS_HERMES_SOURCE=hermes, LIFEOS_MEMORY_SOURCE=native, LIFEOS_TASK_HOOK_PATH=native+'/hooks/TaskGovernance.hook.ts')
command = [sys.executable, '-W', 'error::ResourceWarning', '-m', 'unittest', '-v', 'test_memory_atlas_retention', 'test_memory_atlas_capacity.MemoryAtlasCapacityTests']
source = [*repo.glob('lifeos_hook_bridge/memory_atlas*.py'),repo/'lifeos_hook_bridge/memory_access.py',repo/'lifeos_hook_bridge/memory_service.py',repo/'lifeos_hook_bridge/cli.py']
hashes = {str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
start = time.monotonic()
result = subprocess.run(command, cwd=repo, env=environment, capture_output=True, text=True)
(out/'focused.stdout').write_text(result.stdout)
(out/'focused.stderr').write_text(result.stderr)
(out/'focused.json').write_text(json.dumps({'command':command,'environment_overrides':{k:environment[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH','LIFEOS_HERMES_SOURCE','LIFEOS_MEMORY_SOURCE','LIFEOS_TASK_HOOK_PATH')},'exit_code':result.returncode,'duration_seconds':time.monotonic()-start,'source_hashes':hashes,'unchanged':all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==digest for p,digest in hashes.items())},indent=2)+'\n')
(out/'focused.done').write_text(str(result.returncode)+'\n')
