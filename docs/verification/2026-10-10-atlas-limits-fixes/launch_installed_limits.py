# ABOUTME: Detaches installed acceptance with persistent output and completion evidence.
# ABOUTME: Starts only the candidate verification script as the existing test account.
from pathlib import Path
import json
import subprocess
import sys
here = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-0.2.0-5163a0ce')
with (here/'installed-limits.launch').open('w') as output:
    process = subprocess.Popen([sys.executable,str(here/'run_installed_limits.py')],
        stdin=subprocess.DEVNULL,stdout=output,stderr=output,start_new_session=True)
print(json.dumps({'pid':process.pid,'candidate':str(here),'detached':True}))
