# ABOUTME: Verifies native shutdown and on-demand child cleanup against installed dependencies.
# ABOUTME: Captures actual regression results without activating a messaging transport.
import json
import os
from pathlib import Path
import subprocess
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
package = stage / 'package'
installed = Path(json.loads((stage / 'applications-prepared.json').read_text())['installed'])
environment = {'HOME': '/home/lifeos-hermes', 'PATH': '/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'LANG': 'C.UTF-8', 'TZ': 'America/Toronto', 'TMPDIR': str(stage / 'synthetic-controls'),
    'PYTHONPATH': os.pathsep.join((str(stage / 'shutdown-test-overrides'), str(package),
        str(package / 'tests'), str(package / 'hermes'))),
    'LIFEOS_MEMORY_SOURCE': str(installed), 'LIFEOS_HERMES_SOURCE': str(package / 'hermes'),
    'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'LIFEOS_HARVEST_CONTROL_SOURCE': str(stage / 'native-control-base/LifeOS/install')}
cases = ['test_memory_menubar.MemoryMenubarTests.' + name for name in (
    'test_admitted_daemon_job_counts_preserve_native_metadata',
    'test_original_native_payload_counts_feed_and_initialization_characterization',
    'test_owner_admitted_fields_match_actual_native_payload')]
result = subprocess.run([sys.executable, '-W', 'error', '-m', 'unittest', '-v', *cases],
    cwd=package, env=environment)
sys.exit(result.returncode)
