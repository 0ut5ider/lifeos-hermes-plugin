from pathlib import Path
import subprocess,json
out=Path(__file__).resolve().parent;root=out.parents[2]
command=['/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python','-B',str(out/'closure_controls.py')]
(out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
with (out/'controls.stdout').open('w') as stdout,(out/'controls.stderr').open('w') as stderr:
 result=subprocess.run(command,cwd=root,stdout=stdout,stderr=stderr)
(out/'.done').write_text(str(result.returncode)+'\n')
