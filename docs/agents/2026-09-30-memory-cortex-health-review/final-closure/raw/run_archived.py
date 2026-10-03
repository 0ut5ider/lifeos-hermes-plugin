from pathlib import Path
import subprocess,os,json,hashlib
r=Path(__file__).resolve().parent
base=r.parent.parent
env=dict(os.environ,PYTHONPATH='.:tests',LIFEOS_MEMORY_SOURCE='/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/lifeos/LifeOS/install')
results=[]
for location in ('closure/raw/probe_clock_shapes.py','closure/raw/probe_unmanaged_clock.py','raw/probe_health_edges.py','raw/probe_controls.py','closure/raw/probe_request_bounds.py'):
 script=base/location
 command=['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python',str(script)]
 result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=180)
 (r/(script.stem+'.txt')).write_text(result.stdout+result.stderr)
 results.append(dict(argv=command,sha256=hashlib.sha256(script.read_bytes()).hexdigest(),returncode=result.returncode,stderr=result.stderr))
(r/'archived-results.json').write_text(json.dumps(results,indent=2)+'\n')
