# ABOUTME: Verifies the combined daily text behavior against one sealed native package.
# ABOUTME: Retains exact source identities, commands, complete output, and completion markers.
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
root=Path(__file__).resolve().parents[3]
out=Path(__file__).parent
package=Path(sys.argv[1])
label=sys.argv[2]
hermes=package/'hermes'
native=Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
environment=os.environ|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root)+':'+str(root/'tests')+':'+str(hermes),
 'LIFEOS_HERMES_SOURCE':str(hermes),'LIFEOS_MEMORY_SOURCE':str(native),
 'LIFEOS_FRESH_SOURCE':str(package/'lifeos'),'LIFEOS_TAB_STATE_SOURCE':str(native),
 'LIFEOS_HARVEST_CONTROL_SOURCE':'/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install'}
command=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python','-W','error::ResourceWarning','-m','unittest','-v',*sys.argv[3:]]
record={'command':command,'package_manifest':json.loads((package/'DAILY-CANDIDATE.json').read_text()),
 'source_hashes':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'lifeos_hook_bridge').rglob('*') if p.is_file() and '__pycache__' not in p.parts}}
started=time.monotonic()
result=subprocess.run(command,cwd=root,env=environment,capture_output=True,text=True)
record.update(exit_code=result.returncode,elapsed_seconds=time.monotonic()-started,stdout=result.stdout,stderr=result.stderr)
(out/(label+'.json')).write_text(json.dumps(record,indent=2)+'\n')
(out/(label+'.done')).write_text(str(result.returncode)+'\n')
