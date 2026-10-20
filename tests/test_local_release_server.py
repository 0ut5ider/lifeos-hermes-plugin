# ABOUTME: Checks that the loopback release server runs as a standalone copied script.
# ABOUTME: Qualification copies the script to a test host without the plugin package.
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from optional.lifeos_release_manager.release_catalog import REPOSITORY

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/local_release_server.py'


class LocalReleaseServerTests(unittest.TestCase):
    def test_copied_script_runs_without_the_plugin_package(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / 'local_release_server.py'
            shutil.copy2(SCRIPT, copy)
            result = subprocess.run([sys.executable, '-I', '-B', str(copy), '--help'],
                                    capture_output=True, text=True, timeout=60, cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_served_repository_is_the_catalog_repository(self):
        namespace = {}
        source = SCRIPT.read_text()
        line = next(item for item in source.splitlines() if item.startswith('REPOSITORY = '))
        exec(line, namespace)
        self.assertEqual(namespace['REPOSITORY'], REPOSITORY)


if __name__ == '__main__':
    unittest.main()
