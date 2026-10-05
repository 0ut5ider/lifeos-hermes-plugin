# ABOUTME: Runs authenticated preparation with actual Hermes sessions and native installation.
# ABOUTME: Retains its output and exit marker across an agent disconnect.
from pathlib import Path
import json,os,subprocess
root=Path(__file__).resolve().parent
settings=json.loads((root/'http-command.json').read_text())
with (root/'http-output.txt').open('w') as output:
 result=subprocess.run(settings['command'],cwd=settings['cwd'],env=os.environ|settings['environment'],stdout=output,stderr=subprocess.STDOUT)
(root/'http.done').write_text(str(result.returncode)+'\n')
