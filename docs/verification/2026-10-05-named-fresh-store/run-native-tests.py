# ABOUTME: Repeats the complete named-store test using its recorded native source environment.
# ABOUTME: Retains full test output and its exit marker outside the active agent session.
import json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
settings=json.loads((root/'named-store-command.json').read_text())
with (root/'named-store-output.txt').open('w') as output:
 result=subprocess.run(settings['command'],cwd=settings['cwd'],env=os.environ|settings['environment'],stdout=output,stderr=subprocess.STDOUT)
(root/'named-store.done').write_text(str(result.returncode)+'\n')
