# ABOUTME: Runs isolated paired generic controls and persists completion status.
# ABOUTME: Keeps the experiment alive after the launching SSH session disconnects.
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
cases=['generic-reminder-router', 'generic-memory-turn', 'generic-algorithm-nudge', 'generic-model-rung', 'generic-prompt-processing', 'generic-tab-state', 'generic-voice-completion', 'generic-spend-auditor', 'generic-stop-gates', 'generic-memory-review', 'generic-stop-health', 'generic-integrity-check']
command=['python3',str(root/'paired_lifecycle_effects.py'),'run',str(root/'configuration.json'),str(root/'results')]
for case in cases:
    command.extend(['--case',case])
with (root/'run-output.txt').open('w') as output:
    result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
(root/'run.done').write_text(str(result.returncode)+'\n')
