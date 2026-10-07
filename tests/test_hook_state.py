# ABOUTME: Checks session-state locks across actual processes and abrupt process death.
# ABOUTME: Verifies private-file admission and independent-session progress.
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from lifeos_hook_bridge.hook_state import session_state


class HookStateTests(unittest.TestCase):
    def launch(self, root, session):
        marker = root / (session + '.ready')
        code = ('import sys,time\nfrom pathlib import Path\nfrom lifeos_hook_bridge.hook_state import session_state\n'
                'with session_state(Path(sys.argv[1]),sys.argv[2]):\n'
                ' Path(sys.argv[3]).touch()\n time.sleep(30)\n')
        process = subprocess.Popen([sys.executable, '-c', code, str(root), session, str(marker)],
                                   cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop, process)
        return process, marker

    def stop(self, process):
        if process.poll() is None:
            process.kill()
        out, err = process.communicate(timeout=5)
        self.assertEqual(out, b'')
        self.assertEqual(err, b'')

    def wait_marker(self, marker):
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(marker.exists())

    def test_same_session_waits_and_abrupt_exit_releases_the_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, marker = self.launch(root, 'shared')
            self.wait_marker(marker)
            marker.unlink()
            second, marker = self.launch(root, 'shared')
            time.sleep(.1)
            self.assertFalse(marker.exists())
            self.stop(first)
            self.wait_marker(marker)
            self.assertIsNone(second.poll())

    def test_other_sessions_do_not_wait_for_the_held_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, marker = self.launch(root, 'first')
            self.wait_marker(marker)
            second, other = self.launch(root, 'second')
            self.wait_marker(other)
            self.assertIsNone(first.poll())
            self.assertIsNone(second.poll())

    def test_symlink_and_shared_permissions_cannot_select_a_lock_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'LIFEOS/MEMORY/STATE'
            state.mkdir(parents=True)
            target = root / 'outside'
            target.mkdir(mode=0o700)
            lockdir = state / 'hermes-post-locks'
            lockdir.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, 'private owner directory'):
                with session_state(root, 'fixture'):
                    self.fail('Symlink selected a lock')
            lockdir.unlink()
            lockdir.mkdir(mode=0o755)
            with self.assertRaisesRegex(RuntimeError, 'private owner directory'):
                with session_state(root, 'fixture'):
                    self.fail('Shared directory selected a lock')
