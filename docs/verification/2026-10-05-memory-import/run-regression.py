# ABOUTME: Runs the complete import and neighboring native regression outside the active session.
# ABOUTME: Retains the exact command, complete output, and an exit marker for recovery.
import json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
settings=json.loads((root/'regression-command.json').read_text())
with (root/'regression-output.txt').open('w') as output:
 result=subprocess.run(settings['command'],cwd=settings['cwd'],env=os.environ|settings['environment'],stdout=output,stderr=subprocess.STDOUT)
(root/'regression.done').write_text(str(result.returncode)+'\n')
