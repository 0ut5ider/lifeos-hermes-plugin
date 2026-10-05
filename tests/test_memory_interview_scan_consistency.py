# ABOUTME: Changes sources and authority after actual native interview scan rendering.
# ABOUTME: Verifies that obsolete scan output never reaches the caller.
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_interview_scan as scan_fixture


class MemoryInterviewScanConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = scan_fixture.MemoryInterviewScanTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_post_render_source_owner_installation_and_evidence_changes_refuse_delivery(self):
        configuration = self.fixture.fixture.fixture.fixture.configuration
        baseline = configuration.load()
        for mode in ('source', 'authority', 'installation', 'evidence'):
            with self.subTest(mode=mode):
                configuration.update(lambda value: value.update(baseline))
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_interview_scan_process.py')),
                    str(self.fixture.fixture.fixture.fixture.configuration.path), mode],
                    env=self.fixture.fixture.fixture.environment(), capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                value = json.loads(result.stdout)
                self.assertFalse(value['ok'])
                self.assertNotIn('overall_complete', result.stdout)
                self.assertNotIn('Synthetic assistant', result.stdout)
