# ABOUTME: Exercises owner job deadlines and cancellation against real process groups.
# ABOUTME: Checks that native child lifetimes cannot escape a terminated owner command.
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from lifeos_hook_bridge.memory_owner_jobs import _command


class MemoryOwnerJobProcessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='owner-job-process-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pids = self.root / 'pids.json'
        self.program = self.root / 'child.py'
        self.program.write_text('import json, os, subprocess, sys, time\n'
            'from pathlib import Path\n'
            'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
            f'Path({str(self.pids)!r}).write_text(json.dumps([os.getpid(), child.pid]))\n'
            'time.sleep(60)\n')

    def assert_stopped(self):
        self.assertTrue(self.pids.is_file())
        for pid in json.loads(self.pids.read_text()):
            path = Path('/proc') / str(pid) / 'stat'
            # A killed grandchild can await the operating system's parent reaper.
            self.assertTrue(not path.exists() or path.read_text().rsplit(')', 1)[1].split()[0] == 'Z',
                            f'Child {pid} still runs')

    def test_deadline_kills_the_actual_child_and_grandchild(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            _command([sys.executable, str(self.program)], dict(os.environ), 1)
        self.assert_stopped()

    def test_termination_kills_the_actual_child_and_grandchild(self):
        code = 'import os, sys; from lifeos_hook_bridge.memory_owner_jobs import _command; '
        code += '_command([sys.executable, sys.argv[1]], dict(os.environ), 20)'
        process = subprocess.Popen([sys.executable, '-c', code, str(self.program)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not self.pids.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(self.pids.is_file())
            process.send_signal(signal.SIGTERM)
            output, errors = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143, errors)
            self.assertEqual(output + errors, b'')
            self.assert_stopped()
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == '__main__':
    unittest.main()
