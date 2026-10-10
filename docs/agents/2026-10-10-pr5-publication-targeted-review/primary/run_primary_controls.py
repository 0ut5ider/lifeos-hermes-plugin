# ABOUTME: Repeats the final publication controls gate for the primary reviewer.
# ABOUTME: Retains the source identity, exact command, outputs, and completion marker.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
out = Path(__file__).parent
request = json.loads((out/'controls-request.json').read_text())
root = Path(request['cwd'])
start = time.time()
request['revision'] = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
paths = subprocess.check_output(['git','diff','--name-only','bf53c16dd23d72c9824843cbb85f31db5a48e723..HEAD','--','lifeos_hook_bridge','tests'], cwd=root, text=True).splitlines()
request['source_hashes'] = {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
with (out/'controls-stdout.txt').open('w') as stdout, (out/'controls-stderr.txt').open('w') as stderr:
    run = subprocess.run(request['command'], cwd=root, env=dict(os.environ, **request['environment_overrides']), stdout=stdout, stderr=stderr)
request['exit_code'] = run.returncode
request['duration_seconds'] = time.time()-start
(out/'controls-result.json').write_text(json.dumps(request, indent=2)+'\n')
(out/'controls.done').write_text(str(run.returncode)+'\n')
