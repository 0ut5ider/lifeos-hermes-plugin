# ABOUTME: Builds a committed private removal checkpoint without publishing or selecting a release.
# ABOUTME: Records the real build result and leaves completion evidence outside active servers.
import json
from pathlib import Path
import subprocess
import time

repo=Path(__file__).resolve().parents[3]
cache=Path('/home/outsider/.cache/lifeos-memory-portability-20261015')
base=Path('/home/outsider/.cache/lifeos-daily-promotion-20261014')
python=base/'frozen-test-environment/bin/python'
command=[str(python),'-B',str(repo/'scripts/build_managed_release.py'),'--output',str(cache/'removal-workflow-packages'),
    '--hermes-source',str(base/'upstream-hermes'),'--lifeos-source',str(base/'upstream-lifeos'),
    '--python-closure','/home/outsider/.cache/lifeos-release-0.5.0-20261014/packages/0.5.0-04efe633/python-runtime']
started=time.monotonic()
head=subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True,check=True).stdout.strip()
label='removal-checkpoint-build-'+head[:8]
with (cache/(label+'.stdout')).open('wb') as stdout,(cache/(label+'.stderr')).open('wb') as stderr:
    result=subprocess.run(command,cwd=repo,stdout=stdout,stderr=stderr,timeout=1800)
receipt={'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started,'commit':head,
    'qualified_release':False,'selected_live':False,'daily_changed':False}
(cache/(label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
(cache/(label+'.done')).write_text(str(result.returncode)+'\n')
raise SystemExit(result.returncode)
