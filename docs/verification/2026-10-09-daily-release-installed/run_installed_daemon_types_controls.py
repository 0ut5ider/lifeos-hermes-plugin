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
    'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
cases = ['test_pulse_shutdown', 'test_native_hermes_health_sources', 'test_memory_menubar',
    'test_memory_conduit_jobs.MemoryConduitJobRelayTests.test_native_pulse_shutdown_ends_actual_held_inference_children',
    'test_memory_atlas_jobs.MemoryAtlasJobRelayTests.test_native_pulse_shutdown_ends_actual_atlas_inference_children',
    'test_memory_algorithm_jobs.MemoryAlgorithmJobRelayTests.test_native_pulse_shutdown_ends_actual_summary_children']
result = subprocess.run([sys.executable, '-W', 'error', '-m', 'unittest', '-v', *cases],
    cwd=package, env=environment)
sys.exit(result.returncode)
