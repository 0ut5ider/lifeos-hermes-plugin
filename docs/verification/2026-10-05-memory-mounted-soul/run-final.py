# ABOUTME: Runs managed full-policy soul and native prompt publication controls.
# ABOUTME: Saves output and exit status for detached continuation.
import json, os, subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
s=json.loads((p/'final-command.json').read_text())
with (p/'final-output.txt').open('w') as log:
 r=subprocess.run(s['command'],cwd=s['cwd'],env={**os.environ,**s['environment']},stdout=log,stderr=subprocess.STDOUT)
(p/'final.done').write_text(str(r.returncode)+'\n')
