# ABOUTME: Runs one retained acceptance operator with a durable numeric completion marker.
# ABOUTME: Refuses to overwrite earlier output and records the actual subprocess status.
import json
import os
from pathlib import Path
import subprocess
import sys
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
name, label = sys.argv[1:]
if Path(name).name != name or Path(label).name != label:
    raise ValueError('Choose a fixed local operator and output label')
output = stage / (label + '.txt')
if output.exists():
    raise RuntimeError('The operator output already exists')
python = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
os.umask(0o077)
started = time.monotonic()
with output.open('w') as stream:
    result = subprocess.run([python, '-I', '-B', str(stage / name)], cwd=stage,
        stdout=stream, stderr=subprocess.STDOUT)
(stage / (label + '.done')).write_text(str(result.returncode) + '\n')
(stage / (label + '-status.json')).write_text(json.dumps({'exit_code': result.returncode,
    'elapsed_seconds': round(time.monotonic() - started, 3), 'operator': name}, indent=2) + '\n')
sys.exit(result.returncode)
