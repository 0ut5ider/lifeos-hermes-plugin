# ABOUTME: Runs text transport regression and adjacent delivery controls in local fixtures.
# ABOUTME: Retains command output and a completion marker for the operator correction.
import json,os,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[3]
out=Path(__file__).parent
package=Path('/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-11577ed4')
native=Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
env=os.environ|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':f'{root}:{root/"tests"}:{package/"hermes"}',
 'LIFEOS_HERMES_SOURCE':str(package/'hermes'),'LIFEOS_MEMORY_SOURCE':str(native),
 'LIFEOS_TAB_STATE_SOURCE':str(native),'LIFEOS_FRESH_SOURCE':str(package/'lifeos'),
 'LIFEOS_HARVEST_CONTROL_SOURCE':'/home/outsider/.cache/lifeos-plugin-memory/source/LifeOS/install'}
command=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python','-W','error::ResourceWarning','-m','unittest','-v',
 'test_daily_morning_delivery','test_discord_private_delivery','test_discord_audience','test_memory_atlas_guest_recovery']
start=time.monotonic()
with (out/'combined.stdout').open('w') as stdout,(out/'combined.stderr').open('w') as stderr:
 result=subprocess.run(command,cwd=root,env=env,stdout=stdout,stderr=stderr)
(out/'combined.json').write_text(json.dumps({'command':command,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-start,3)},indent=2)+'\n')
(out/'combined.done').write_text(str(result.returncode)+'\n')
