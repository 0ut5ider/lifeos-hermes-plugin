# ABOUTME: Executes synthetic destination probes with recorded source and native environments.
# ABOUTME: Saves process results and a completion marker independently of the active session.
import os,json,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[3];o=Path(__file__).parent;p=json.loads((r/'docs/verification/2026-10-10-publication-review-fixes/final-recovery-invariants.json').read_text());cmd=[p['command'][0],str(o/'probe_destination_families.py')];start=time.time()
x=subprocess.run(cmd,cwd=r,env=dict(os.environ,**p['environment_overrides']),capture_output=True,text=True)
(o/'destination-families.json').write_text(json.dumps({'command':cmd,'cwd':str(r),'environment_overrides':p['environment_overrides'],'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),'stdout':x.stdout,'stderr':x.stderr,'exit_code':x.returncode,'duration_seconds':time.time()-start},indent=2)+'\n');(o/'destination-families.done').write_text(str(x.returncode)+'\n')
