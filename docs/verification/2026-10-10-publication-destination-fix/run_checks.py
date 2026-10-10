# ABOUTME: Runs publication destination regressions against real prepared native sources.
# ABOUTME: Retains exact commands, source hashes, output, and completion status.
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
record = json.loads((root/'docs/verification/2026-10-10-publication-review-fixes/final-recovery-invariants.json').read_text())
command = [record['command'][0], '-m', 'unittest', '-v', *sys.argv[2:]]
paths = ['lifeos_hook_bridge/'+name for name in ('memory_algorithm_summary.py', 'memory_local_refresh.py', 'memory_conduit_insight.py')] + ['tests/test_memory_publication_destinations.py']
request = {'command': command, 'cwd': str(root), 'environment_overrides': record['environment_overrides'],
    'revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    'source_hashes': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}}
(out/(label+'.request.json')).write_text(json.dumps(request,indent=2)+'\n')
start = time.time()
with (out/(label+'.stdout.txt')).open('w') as stdout, (out/(label+'.stderr.txt')).open('w') as stderr:
    run = subprocess.run(command,cwd=root,env=dict(os.environ,**request['environment_overrides']),stdout=stdout,stderr=stderr)
request.update(exit_code=run.returncode,duration_seconds=time.time()-start)
(out/(label+'.json')).write_text(json.dumps(request,indent=2)+'\n')
(out/(label+'.done')).write_text(str(run.returncode)+'\n')
