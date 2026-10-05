# ABOUTME: Runs the recorded synthetic Hermes soul publication gate.
# ABOUTME: Saves complete output and an exit marker for detached continuation.
import json,subprocess,os
from pathlib import Path
p=Path(__file__).resolve().parent
s=json.loads((p/'retirement-controls-command.json').read_text())
with (p/'retirement-controls-output.txt').open('w') as log:
 r=subprocess.run(s['command'],cwd=s['cwd'],env={**os.environ,**s['environment']},stdout=log,stderr=subprocess.STDOUT)
(p/'retirement-controls.done').write_text(str(r.returncode)+'\n')
