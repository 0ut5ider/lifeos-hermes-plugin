# ABOUTME: Runs isolated asynchronous paired feedback controls and persists completion status.
# ABOUTME: Keeps the experiment alive after the launching SSH session disconnects.
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
cases=['feedback-async-rating','feedback-async-bare-rating','feedback-async-praise','feedback-async-neutral','feedback-async-low-rating']
command=['python3',str(root/'paired_lifecycle_effects.py'),'run',str(root/'configuration.json'),str(root/'results')]
for case in cases:
    command.extend(['--case',case])
with (root/'run-output.txt').open('w') as output:
    result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
(root/'run.done').write_text(str(result.returncode)+'\n')
