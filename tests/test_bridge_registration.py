# ABOUTME: Checks the per-process bridge registration receipts that prove a restarted service's hook mode.
# ABOUTME: Uses real processes; receipts of dead or reused process IDs are not accepted.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lifeos_hook_bridge.registration import directory, read_receipt, write_receipt


class RegistrationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.profile = Path(self.folder.name)

    def test_this_process_receipt_round_trips(self):
        value = write_receipt(self.profile, 'patched')
        self.assertEqual(read_receipt(self.profile, os.getpid()), value)
        self.assertEqual(directory(self.profile).stat().st_mode & 0o777, 0o700)

    def test_receipt_with_another_start_time_is_not_accepted(self):
        write_receipt(self.profile, 'patched')
        path = directory(self.profile) / (str(os.getpid()) + '.json')
        value = json.loads(path.read_text())
        path.write_text(json.dumps({**value, 'start_time': value['start_time'] + 1}))
        self.assertIsNone(read_receipt(self.profile, os.getpid()))

    def test_dead_process_receipts_are_pruned(self):
        child = subprocess.run([sys.executable, '-c', 'print(1)'], capture_output=True)
        stale = directory(self.profile)
        stale.mkdir(parents=True)
        dead = stale / '999999999.json'
        dead.write_text('{}')
        write_receipt(self.profile, 'reduced')
        self.assertFalse(dead.exists())
        self.assertEqual(child.returncode, 0)

    def test_receipt_records_the_hermes_checkout_that_the_process_imports(self):
        import hermes_cli
        value = write_receipt(self.profile, 'patched')
        self.assertEqual(value['source'], str(Path(hermes_cli.__file__).resolve().parents[1]))
        self.assertEqual(read_receipt(self.profile, os.getpid())['source'], value['source'])

    def test_unknown_mode_is_refused(self):
        with self.assertRaises(ValueError):
            write_receipt(self.profile, 'complete')


if __name__ == '__main__':
    unittest.main()
