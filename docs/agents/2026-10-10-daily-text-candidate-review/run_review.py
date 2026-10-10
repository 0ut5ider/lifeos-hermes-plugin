# ABOUTME: Records isolated review command execution and exact outputs.
# ABOUTME: Uses the provided prepared native sources without changing shared files.
from pathlib import Path
import json, os, subprocess, sys, time
ROOT=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT=Path(__file__).parent
ENV=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT)+':'+str(ROOT/'tests')+':/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes', LIFEOS_HERMES_SOURCE='/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes', LIFEOS_MEMORY_SOURCE='/home/outsider/.cache/lifeos-daily-text-20261007/content-response-first/lifeos/LifeOS/install', LIFEOS_HARVEST_CONTROL_SOURCE='/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install')
command=sys.argv[2:]
start=time.time()
r=subprocess.run(command,cwd=ROOT,env=ENV,text=True,capture_output=True)
record={'command':command,'cwd':str(ROOT),'environment_overrides':{k:ENV[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH','LIFEOS_HERMES_SOURCE','LIFEOS_MEMORY_SOURCE','LIFEOS_HARVEST_CONTROL_SOURCE')},'exit_code':r.returncode,'duration_seconds':time.time()-start,'stdout':r.stdout,'stderr':r.stderr}
(OUT/(sys.argv[1]+'.json')).write_text(json.dumps(record,indent=2))
(OUT/(sys.argv[1]+'.log')).write_text(r.stdout+r.stderr)
print(json.dumps({k:record[k] for k in ('command','exit_code','duration_seconds')}))
print(r.stdout[-2500:]);print(r.stderr[-2500:])
sys.exit(r.returncode)
