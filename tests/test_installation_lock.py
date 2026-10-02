# ABOUTME: Exercises installation exclusion and process-exit recovery with real file locks.
# ABOUTME: Verifies private lock paths and blocking detached-worker handoff.

import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import unittest

from lifeos_hook_bridge.installation_lock import installation_lock


class InstallationLockTests(unittest.TestCase):
    def child(self, profile, *, wait):
        code = ('from pathlib import Path\n'
                'from lifeos_hook_bridge.installation_lock import installation_lock\n'
                'import sys\n'
                f'with installation_lock(Path(sys.argv[1]), wait={wait!r}):\n'
                ' print("acquired", flush=True)\n'
                ' sys.stdin.readline()\n')
        child = subprocess.Popen([sys.executable, '-c', code, str(profile)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.finish, child)
        return child

    @staticmethod
    def finish(child):
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)

    def test_other_process_cannot_admit_or_execute_while_owner_holds_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile):
                child = self.child(profile, wait=False)
                output, error = child.communicate(timeout=5)
                self.assertNotEqual(child.returncode, 0)
                self.assertEqual(output, '')
                self.assertIn('Another installation operation is running', error)
            with installation_lock(profile):
                self.assertEqual((profile / '.lifeos-installation/lock').stat().st_mode & 0o777, 0o600)

    def test_detached_worker_waits_for_admission_then_process_death_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile):
                child = self.child(profile, wait=True)
                self.assertEqual(select.select([child.stdout], [], [], 0.1)[0], [])
            self.assertTrue(select.select([child.stdout], [], [], 5)[0])
            self.assertEqual(child.stdout.readline(), 'acquired\n')
            with self.assertRaisesRegex(RuntimeError, 'Another installation operation'):
                with installation_lock(profile):
                    self.fail('A second operation acquired the live worker lock')
            os.kill(child.pid, signal.SIGKILL)
            _, error = child.communicate(timeout=5)
            self.assertEqual(child.returncode, -signal.SIGKILL)
            self.assertEqual(error, '')
            with installation_lock(profile):
                pass

    def test_unsafe_lock_directory_and_file_are_refused(self):
        for mutation in ('directory permissions', 'directory link', 'file permissions', 'file link'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                profile = Path(directory)
                state = profile / '.lifeos-installation'
                state.mkdir(mode=0o700)
                lock = state / 'lock'
                lock.write_text('')
                lock.chmod(0o600)
                if mutation == 'directory permissions':
                    state.chmod(0o755)
                elif mutation == 'directory link':
                    state.rename(profile / 'external')
                    state.symlink_to(profile / 'external', target_is_directory=True)
                elif mutation == 'file permissions':
                    lock.chmod(0o644)
                else:
                    lock.rename(state / 'external')
                    lock.symlink_to(state / 'external')
                with self.assertRaises((RuntimeError, OSError)):
                    with installation_lock(profile):
                        self.fail('Unsafe installation lock was accepted')
