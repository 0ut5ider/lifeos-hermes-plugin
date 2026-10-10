# ABOUTME: Runs the installed release checks in sequence with durable per-command evidence.
# ABOUTME: Keeps services, state changes, failures, and completion tied to the frozen candidate.
import json
import os
from pathlib import Path
import subprocess
import sys
import time

here=Path(__file__).resolve().parent
os.umask(0o077)
commands=['verify_runtime.py','verify_fresh.py','verify_cancellation.py','verify_applications.py',
          'run_owner_turn.py','verify_owner_turn.py','verify_atlas.py','verify_schedule.py',
          'verify_active_stop.py','verify_profile_recovery.py','verify_rollback.py','verify_runtime.py']
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
assert 0<=start<len(commands)
observations=json.loads((here/'progress.json').read_text())[:start] if start else []
assert len(observations)==start and all(row['exit_code']==0 for row in observations)
status=0
try:
    for index in range(start,len(commands)):
        name=commands[index]
        started=time.monotonic()
        with (here/(str(index)+'-'+name+'.stdout')).open('w') as output, (here/(str(index)+'-'+name+'.stderr')).open('w') as errors:
            result=subprocess.run([sys.executable,str(here/name)],stdout=output,stderr=errors,timeout=900)
        row={'program':name,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started}
        observations.append(row)
        (here/'progress.json').write_text(json.dumps(observations,indent=2)+'\n')
        print(json.dumps(row),flush=True)
        if result.returncode:
            status=result.returncode
            break
except BaseException as error:
    status=1
    observations.append({'supervisor_error':str(error)})
finally:
    (here/'result.json').write_text(json.dumps({'status':'PASS' if status==0 else 'FAIL','commands':observations},indent=2)+'\n')
    (here/'.done').write_text(str(status)+'\n')
