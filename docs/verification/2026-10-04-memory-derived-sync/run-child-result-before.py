# ABOUTME: Runs the recorded synthetic derivative publication gate.
# ABOUTME: Saves complete output and an exit marker for detached continuation.
import json,subprocess,os
from pathlib import Path
p=Path(__file__).resolve().parent
s=json.loads((p/'child-result-before-command.json').read_text())
with (p/'child-result-before-output.txt').open('w') as log:
 r=subprocess.run(s['command'],cwd=s['cwd'],env={**os.environ,**s['environment']},stdout=log,stderr=subprocess.STDOUT)
(p/'child-result-before.done').write_text(str(r.returncode)+'\n')
