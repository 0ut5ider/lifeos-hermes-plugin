# ABOUTME: Runs isolated paired generic tool controls and persists completion status.
# ABOUTME: Keeps the experiment alive after the launching SSH session disconnects.
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
cases=['generic-tool-observer', 'generic-tool-failure-nudge', 'generic-tool-context-reduction']
command=['python3',str(root/'paired_lifecycle_effects.py'),'run',str(root/'configuration.json'),str(root/'results')]
for case in cases:
    command.extend(['--case',case])
with (root/'run-output.txt').open('w') as output:
    result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
(root/'run.done').write_text(str(result.returncode)+'\n')
