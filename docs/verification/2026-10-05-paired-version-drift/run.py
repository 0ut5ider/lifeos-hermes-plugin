# ABOUTME: Runs isolated paired version-drift controls and persists completion status.
# ABOUTME: Keeps the experiment alive after the launching SSH session disconnects.
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
cases=['version-drift-count','version-drift-aged','version-drift-below','version-drift-bump','version-drift-recent','version-drift-untagged','version-drift-async-count']
command=['python3',str(root/'paired_lifecycle_effects.py'),'run',str(root/'configuration.json'),str(root/'results')]
for case in cases:
    command.extend(['--case',case])
with (root/'run-output.txt').open('w') as output:
    result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
(root/'run.done').write_text(str(result.returncode)+'\n')
