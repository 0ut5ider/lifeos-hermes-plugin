# ABOUTME: Checks PULSE publication against real later destination edits.
# ABOUTME: Requires log and page operations to refuse stale writes without losing those edits.
import json
from pathlib import Path
import subprocess
import sys
import unittest

from test_memory_pulse_adapter_data import MemoryPulseAdapterDataTests


class MemoryPulseAdapterDestinationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = MemoryPulseAdapterDataTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.fixture.fixture.configuration

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_pulse_adapter_destination_process.py')),
            str(self.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        outcome = json.loads(result.stdout)
        self.assertFalse(outcome['result']['ok'], outcome)
        self.assertTrue(outcome['preserved'], outcome)

    def test_later_log_append_is_preserved(self):
        self.process('log')

    def test_later_page_edit_is_preserved(self):
        self.process('page')
