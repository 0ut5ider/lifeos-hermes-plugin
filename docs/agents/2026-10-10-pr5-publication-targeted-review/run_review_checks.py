# ABOUTME: Runs independent selected publication checks against the reviewed source.
# ABOUTME: Stores exact commands, source identity, process output and completion status.
import os,json,subprocess,sys,time,hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[3]; o=Path(__file__).parent
prior=json.loads((r/'docs/verification/2026-10-10-publication-review-fixes/final-recovery-invariants.json').read_text())
cmd=prior['command'] if sys.argv[1]=='recovery' else prior['command'][:4]+['test_memory_staging','test_memory_staging_writers','test_memory_publication_recovery','test_memory_native_response_authority']
env=prior['environment_overrides']; start=time.time()
files=subprocess.check_output(['git','ls-files','lifeos_hook_bridge','tests'],cwd=r,text=True).splitlines()
data={'command':cmd,'cwd':str(r),'environment_overrides':env,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),'source_hashes':{f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in files}}
with (o/(sys.argv[1]+'.stdout')).open('w') as out,(o/(sys.argv[1]+'.stderr')).open('w') as err:
 p=subprocess.run(cmd,cwd=r,env=dict(os.environ,**env),stdout=out,stderr=err)
data.update(exit_code=p.returncode,duration_seconds=time.time()-start,stdout=sys.argv[1]+'.stdout',stderr=sys.argv[1]+'.stderr')
(o/(sys.argv[1]+'.json')).write_text(json.dumps(data,indent=2)+'\n');(o/(sys.argv[1]+'.done')).write_text(str(p.returncode)+'\n')
