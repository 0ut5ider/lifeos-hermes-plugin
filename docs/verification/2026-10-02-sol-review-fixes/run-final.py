# ABOUTME: Runs the complete regression against prepared public synthetic fixtures.
# ABOUTME: Records command exits and completion without detached Git operations.
import os,json,subprocess
from pathlib import Path
ROOT=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
OUT=ROOT/'docs/verification/2026-10-02-sol-review-fixes/final'
manifest=json.loads((OUT/'commands.json').read_text())
commands=manifest['commands'];env=dict(os.environ,**manifest['environment'])
for name, command in commands.items():
    with (OUT / (name + '.txt')).open('w') as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    (OUT / (name + '.exit')).write_text(str(result.returncode) + '\n')
(OUT / '.done').touch()
