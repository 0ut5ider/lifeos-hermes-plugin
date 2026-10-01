# ABOUTME: Reruns archived delta probes unchanged against the fresh byte fixture.
# ABOUTME: Records exact arguments, hashes, stdout, stderr, and exit codes.
import os,sys,subprocess,json,hashlib
from pathlib import Path
base=Path('docs/agents/2026-09-30-memory-native-delta-review');out=base/'final-closure/raw'
env=dict(os.environ,PYTHONPATH='.:tests',LIFEOS_MEMORY_SOURCE='/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-delta-bytes/lifeos/LifeOS/install')
results=[]
for script,label in [(base/'raw/probe_delta_shapes.py','shapes'),(base/'raw/probe_delta_volume.py','volume'),(base/'closure/raw/probe_controls.py','controls'),(base/'closure/raw/probe_delta_bytes.py','bytes'),(base/'byte-closure/raw/probe_cursor_samples.py','cursor')]:
 p=subprocess.run([sys.executable,str(script)],text=True,capture_output=True,env=env,timeout=120)
 (out/f'archived-{label}.txt').write_text(p.stdout+p.stderr)
 results.append({'argv':[sys.executable,str(script)],'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'returncode':p.returncode,'stdout_file':f'archived-{label}.txt','stderr':p.stderr})
(out/'archived-results.json').write_text(json.dumps({'environment':{k:env[k] for k in ['PYTHONPATH','LIFEOS_MEMORY_SOURCE']},'results':results},indent=2)+'\n')
print(json.dumps(results))
