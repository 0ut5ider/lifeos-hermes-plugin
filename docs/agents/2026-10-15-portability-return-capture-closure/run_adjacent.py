from pathlib import Path
import subprocess,json,shutil
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent
label='review-return-capture-adjacent'
command=['/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python','docs/verification/2026-10-15-memory-portability/run_tests.py',label,'docs.agents.2026-10-15-portability-return-capture-closure.adjacent_controls']
(out/'adjacent-command.json').write_text(json.dumps(command,indent=2)+'\n')
with (out/'adjacent-supervisor.stdout').open('w') as stdout,(out/'adjacent-supervisor.stderr').open('w') as stderr:
 result=subprocess.run(command,cwd=root,stdout=stdout,stderr=stderr)
for suffix in ('stdout','stderr','json','done'):
 source=root/'docs/verification/2026-10-15-memory-portability'/f'{label}.{suffix}'
 if source.exists():shutil.copyfile(source,out/source.name)
(out/'adjacent.done').write_text(str(result.returncode)+'\n')
