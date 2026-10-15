# ABOUTME: Repeats independent certificate closure controls against frozen current operator sources.
# ABOUTME: Stores only safe validator component results and does not execute a remote operation.
import json
from pathlib import Path
import subprocess
import time
folder=Path(__file__).resolve().parent
command=['/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python','-B',str(folder/'final_closure_controls.py')]
started=time.monotonic()
code=1
try:
    with (folder/'primary.stdout').open('wb') as stdout,(folder/'primary.stderr').open('wb') as stderr:
        code=subprocess.run(command,cwd=folder.parents[2],stdout=stdout,stderr=stderr,timeout=1200).returncode
    (folder/'primary-result.json').write_text(json.dumps({'command':command,'exit_code':code,'elapsed_seconds':time.monotonic()-started,'component_controls_only':True,'qualified_certificate_written':False},indent=2)+'\n')
finally:
    (folder/'primary.done').write_text(str(code)+'\n')
