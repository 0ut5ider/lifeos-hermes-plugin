# ABOUTME: Verifies first-install process discovery against actual synthetic owner processes.
# ABOUTME: Distinguishes Hermes dashboards from unrelated commands with the same argument text.
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from optional.lifeos_release_manager.release_services import check_dashboard_writers
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class ReleaseServiceTests(unittest.TestCase):
    def test_foreground_detection_uses_the_actual_hermes_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = root / '.hermes'
            profile.mkdir(mode=0o700)
            for name, expected in (('unrelated.py', False), ('hermes', True)):
                with self.subTest(name=name):
                    ready = root / (name + '.ready')
                    script = root / name
                    script.write_text('from pathlib import Path\nimport time\n'
                        'Path(' + repr(str(ready)) + ').touch()\ntime.sleep(30)\n')
                    process = subprocess.Popen([sys.executable, '-B', str(script), 'dashboard'],
                        env=dict(os.environ, HERMES_HOME=str(profile)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try:
                        deadline = time.monotonic() + 5
                        while not ready.exists() and time.monotonic() < deadline:
                            time.sleep(0.01)
                        self.assertTrue(ready.exists())
                        if expected:
                            with self.assertRaisesRegex(ReleaseRejected, 'owner user service'):
                                check_dashboard_writers(profile)
                        else:
                            check_dashboard_writers(profile)
                    finally:
                        process.terminate()
                        process.wait(timeout=5)
