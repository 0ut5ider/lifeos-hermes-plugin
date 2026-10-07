# ABOUTME: Exercises model verification logging through actual native adapter inference.
# ABOUTME: Checks private fixed-destination publication and foreign-file preservation.
import json
import unittest

import test_memory_pulse_adapter_inference as inference_fixture


class MemoryInferenceLogTests(unittest.TestCase):
    def setUp(self):
        self.fixture = inference_fixture.MemoryPulseAdapterInferenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.fixture.root
        self.path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/model-verification.jsonl'

    def test_actual_inference_retains_private_native_verification_record(self):
        result = self.fixture.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(len(self.fixture.received), 1)
        entries = [json.loads(line) for line in self.path.read_text().splitlines()]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['level'], 'low')
        self.assertEqual(entries[0]['expected_tier'], 'haiku')
        self.assertEqual(entries[0]['executed'], 'synthetic-flashnext')
        self.assertTrue(entries[0]['downgraded'])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_redirected_log_preserves_foreign_bytes_and_native_inference(self):
        foreign = self.root.parent / 'foreign-verification.jsonl'
        before = b'{"synthetic":"foreign log"}\n'
        foreign.write_bytes(before)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.symlink_to(foreign)
        result = self.fixture.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(foreign.read_bytes(), before)
        self.assertEqual(len(self.fixture.received), 1)
