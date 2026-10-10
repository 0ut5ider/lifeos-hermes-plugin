# ABOUTME: Runs the installed Atlas limits check independently of the interactive session.
# ABOUTME: Retains stdout, stderr, and an exit marker beside the selected candidate.
from pathlib import Path
import subprocess
import sys
here = Path(__file__).resolve().parent
with (here/'installed-limits.stdout').open('w') as output, (here/'installed-limits.stderr').open('w') as errors:
    result = subprocess.run([sys.executable, str(here/'verify_installed_limits.py')], stdout=output, stderr=errors)
(here/'installed-limits.done').write_text(str(result.returncode)+'\n')
