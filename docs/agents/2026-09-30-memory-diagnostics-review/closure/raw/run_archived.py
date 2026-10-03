from pathlib import Path
import subprocess,os,json,hashlib
r=Path(__file__).resolve().parent
old=r.parent.parent/'raw'
env=dict(os.environ,PYTHONPATH='.:tests',LIFEOS_MEMORY_SOURCE='/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-diagnostics-closure/lifeos/LifeOS/install')
results=[]
for name in ('limits','controls','long_control'):
 script=old/('probe_'+name+'.py')
 command=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python',str(script)]
 result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=180)
 (r/('archived-'+name+'.txt')).write_text(result.stdout+result.stderr)
 results.append(dict(argv=command,sha256=hashlib.sha256(script.read_bytes()).hexdigest(),returncode=result.returncode,stderr=result.stderr))
(r/'archived-results.json').write_text(json.dumps(results,indent=2)+'\n')
