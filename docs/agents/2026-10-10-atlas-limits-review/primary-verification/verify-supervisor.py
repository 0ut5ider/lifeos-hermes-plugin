# ABOUTME: Repeats the reviewer capacity, freshness, and backup experiments independently.
# ABOUTME: Preserves the reviewer outputs and writes separate results and completion markers.
from pathlib import Path
import os,subprocess,json,sys
out=Path(__file__).resolve().parent
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests:/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes',LIFEOS_HERMES_SOURCE='/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed/hermes',LIFEOS_MEMORY_SOURCE='/home/outsider/.cache/lifeos-atlas-20261010/native-sync-final/LifeOS/install')
processes=[]
for name in ('managed','backup'):
 output=(out/(name+'.stdout')).open('w');errors=(out/(name+'.stderr')).open('w')
 command=[sys.executable,str(out/(name+'-measure.py'))]
 process=subprocess.Popen(command,env=env,stdout=output,stderr=errors)
 processes.append((name,command,process,output,errors))
results=[]
for name,command,process,output,errors in processes:
 result=process.wait();output.close();errors.close()
 results.append({'experiment':name,'command':command,'exit_code':result,'stderr':(out/(name+'.stderr')).read_text()})
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
(out/'verification.done').write_text(str(int(any(row['exit_code'] for row in results)))+'\n')
