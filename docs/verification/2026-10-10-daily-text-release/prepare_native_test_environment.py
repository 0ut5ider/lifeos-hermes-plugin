# ABOUTME: Prepares the same native test dependencies on Python 3.13 for strict SDK warning controls.
# ABOUTME: Keeps environment setup, dependency versions, failures, and completion separate from application bytes.
from pathlib import Path
import json
import os
import subprocess
import time

here=Path(__file__).resolve().parent
uv='/home/outsider/.cache/hermes-upstream-runtime/uv-0.12.3-linux-x64/uv'
environment=Path('/home/outsider/.cache/lifeos-atlas-20261010/native-test-python313')
commands=[[uv,'venv','--python','3.13',str(environment)],
          [uv,'pip','install','--python',str(environment/'bin/python'),'-r',str(here/'native-test-requirements.txt')]]
rows=[]
status=0
try:
    for command in commands:
        started=time.monotonic()
        result=subprocess.run(command,capture_output=True,text=True,timeout=600)
        rows.append({'command':command,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started,
                     'stdout':result.stdout,'stderr':result.stderr})
        if result.returncode:
            status=result.returncode
            break
except BaseException as error:
    status=1
    rows.append({'error':str(error)})
finally:
    (here/'native-test-environment.json').write_text(json.dumps({'status':'PASS' if status==0 else 'FAIL','commands':rows},indent=2)+'\n')
    (here/'native-test-environment.done').write_text(str(status)+'\n')
