# ABOUTME: Runs actual Hermes learning-memory flag and provider controls.
# ABOUTME: Retains detached output and complete exit markers for both native and bridge checks.
import json, os, subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
s=json.loads((p/'final-command.json').read_text())
for name,cmd,cwd in [('final',s['command'],s['cwd']),('final-native',s['native_tests_command'],s['environment']['LIFEOS_HERMES_SOURCE'])]:
 with (p/(name+'-output.txt')).open('w') as log:
  r=subprocess.run(cmd,cwd=cwd,env={**os.environ,**s['environment']},stdout=log,stderr=subprocess.STDOUT)
 (p/(name+'.done')).write_text(str(r.returncode)+'\n')
