# ABOUTME: Runs Atlas and publication checks against complete prepared native sources.
# ABOUTME: Records exact commands, runtime hashes, captured output, and completion markers.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
root = Path(__file__).resolve().parents[3]
out = Path(__file__).parent
label = sys.argv[1]
environment = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root)+':'+str(root/'tests')+':/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes',
 'LIFEOS_HERMES_SOURCE': '/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes',
 'LIFEOS_MEMORY_SOURCE': '/home/outsider/.cache/lifeos-atlas-20261010/native-sync-final/LifeOS/install',
 'LIFEOS_HARVEST_CONTROL_SOURCE': '/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install'}
command = ['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python', '-m', 'unittest', '-v', *sys.argv[2:]]
paths = ['lifeos_hook_bridge/'+name for name in ('memory_atlas_sync.py', 'memory_atlas_insight.py', 'memory_access.py', 'memory_service.py', 'memory_owner_jobs.py', 'memory_native.ts', 'patches/lifeos-memory-access.patch')] + ['tests/test_memory_atlas_sync.py', 'tests/memory_atlas_sync_process.py']
request = {'command': command, 'cwd': str(root), 'environment_overrides': environment, 'source_hashes': {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}}
(out/(label+'.request.json')).write_text(json.dumps(request,indent=2)+'\n')
started = time.monotonic()
result = subprocess.run(command, cwd=root, env=dict(os.environ,**environment),capture_output=True,text=True)
request.update(exit_code=result.returncode,duration_seconds=time.monotonic()-started,stdout=result.stdout,stderr=result.stderr)
(out/(label+'.json')).write_text(json.dumps(request,indent=2)+'\n')
(out/(label+'.done')).write_text(str(result.returncode)+'\n')
