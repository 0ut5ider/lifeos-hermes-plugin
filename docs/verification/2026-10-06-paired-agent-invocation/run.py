# ABOUTME: Runs a paired delegation and persists its exit status.
# ABOUTME: Stores raw model traffic privately in disposable fixture homes.
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
with (root/'run-output.txt').open('w') as output:
 result=subprocess.run(['python3',str(root/'paired_lifecycle_effects.py'),'run',str(root/'configuration.json'),str(root/'results-final2'),'--case','generic-agent-pre','--case','generic-agent-tier'],stdout=output,stderr=subprocess.STDOUT)
(root/'run.done').write_text(str(result.returncode)+'\n')
