# ABOUTME: Runs native recurrence controls in an isolated test environment.
# ABOUTME: Saves process output and completion status across disconnects.
from pathlib import Path
import json, os, subprocess
p=Path(__file__).parent
s=json.loads((p/'final-command.json').read_text())
with (p/'final-output.txt').open('w') as output:
 result=subprocess.run(s['command'],cwd=s['cwd'],env={**os.environ,**s['environment']},stdout=output,stderr=subprocess.STDOUT)
(p/'final.done').write_text(str(result.returncode)+'\n')
