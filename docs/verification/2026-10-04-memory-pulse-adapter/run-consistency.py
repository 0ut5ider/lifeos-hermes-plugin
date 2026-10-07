# ABOUTME: Runs the recorded synthetic PULSE adapter publication gate.
# ABOUTME: Saves complete output and an exit marker for detached continuation.
import json,subprocess,os
from pathlib import Path
p=Path(__file__).resolve().parent
s=json.loads((p/'consistency-command.json').read_text())
with (p/'consistency-output.txt').open('w') as log:
 r=subprocess.run(s['command'],cwd=s['cwd'],env={**os.environ,**s['environment']},stdout=log,stderr=subprocess.STDOUT)
(p/'consistency.done').write_text(str(r.returncode)+'\n')
