# ABOUTME: Runs a candidate build independently of the interactive session.
# ABOUTME: Saves complete output and an exit marker for subsequent verification.
from pathlib import Path
import subprocess
import sys
here = Path(__file__).resolve().parent
with (here / (sys.argv[1] + '.stdout')).open('w') as output, (here / (sys.argv[1] + '.stderr')).open('w') as errors:
    result = subprocess.run([sys.executable, str(here/'build_candidate.py'), '--tag', sys.argv[1]], stdout=output, stderr=errors)
(here / (sys.argv[1] + '.done')).write_text(str(result.returncode)+'\n')
