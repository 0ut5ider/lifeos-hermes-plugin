# ABOUTME: Runs retained native controls against the isolated installed candidate on .252.
# ABOUTME: Records the real subprocess exit status without nested remote shell quoting.
import json
import os
from pathlib import Path
import subprocess
import sys
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
installed = Path(json.loads((stage / 'fresh-store-installed.json').read_text())['fresh_store_review']['installed'])
python = '/home/lifeos-hermes/.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
temporary = stage / 'synthetic-controls'
temporary.mkdir(mode=0o700, exist_ok=True)
label = 'installed-pulse-command-controls-first'
output = stage / (label + '.txt')
if output.exists():
    raise RuntimeError('The installed control output already exists')
environment = {'HOME': '/home/lifeos-hermes', 'PATH': '/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'LANG': 'C.UTF-8', 'TZ': 'America/Toronto', 'TMPDIR': str(temporary),
    'PYTHONPATH': os.pathsep.join((str(package), str(package / 'tests'), str(package / 'hermes'))),
    'LIFEOS_MEMORY_SOURCE': str(installed), 'LIFEOS_HERMES_SOURCE': str(package / 'hermes'),
    'LIFEOS_HARVEST_CONTROL_SOURCE': str(package / 'lifeos/LifeOS/install'),
    'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
modules = ['test_memory_pulse_relay', 'test_memory_content', 'test_memory_content_actions',
    'test_memory_conduit_capture_job', 'test_daily_conduit_capture', 'test_daily_pulse_profile']
started = time.monotonic()
with output.open('w') as stream:
    result = subprocess.run([python, '-W', 'error', '-m', 'unittest', '-v', *modules],
        env=environment, cwd=package, stdout=stream, stderr=subprocess.STDOUT)
(stage / (label + '.done')).write_text(str(result.returncode) + '\n')
(stage / (label + '-status.json')).write_text(json.dumps({'exit_code': result.returncode,
    'elapsed_seconds': round(time.monotonic() - started, 3), 'modules': modules,
    'installed_source': str(installed), 'synthetic_temporary_directory': str(temporary)}, indent=2) + '\n')
sys.exit(result.returncode)
