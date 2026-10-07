# ABOUTME: Exercises exact source review for decoded scan names and installed setup files.
# ABOUTME: Keeps the generic source reader boundary separate from the scanner's fixed setup inputs.
import unittest

import test_memory_interview_scan as scan_fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_source_review import preview, approve
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryInterviewScanReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = scan_fixture.MemoryInterviewScanTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.fixture.fixture.memory
        self.root = self.fixture.root

    def test_review_rejects_decoded_private_or_retired_assistant_names(self):
        self.fixture.fixture.retire_work()
        relative = 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'
        for name in ('\\u003cprivate\\u003eSyntheticPrivateScanName\\u003c/private\\u003e',
                     '\\u0053ynthetic retired evidence work'):
            with self.subTest(name=name):
                self.fixture.identity.write_text('---\ncore:\n  name: "' + name + '"\n---\n# Synthetic assistant\n')
                snapshot = preview(self.memory, OWNER, [relative])
                self.assertFalse(snapshot['sources'][0]['accepted'])
                self.assertEqual(snapshot['sources'][0]['content'], '')
                self.assertEqual(approve(self.memory, OWNER, [relative], snapshot['signature'])['status'], 'rejected')

    def test_exact_review_restores_old_setup_scoring_without_changing_bytes(self):
        self.fixture.fixture.retire_work()
        paths = ['.env', 'LIFEOS/PULSE/PULSE.toml', 'LIFEOS/USER/WORK/config.yaml']
        before = {relative: (self.root / relative).read_bytes() for relative in paths}
        self.assertEqual(self.fixture.target('WORK/config')['content_length'], 0)
        snapshot = preview(self.memory, OWNER, paths)
        self.assertTrue(all(source['accepted'] for source in snapshot['sources']))
        self.assertEqual(approve(self.memory, OWNER, paths, snapshot['signature'])['status'], 'committed')
        self.assertEqual(self.fixture.target('WORK/config')['content_length'], len(self.fixture.work.read_text()))
        for relative, data in before.items():
            self.assertEqual((self.root / relative).read_bytes(), data)

    def test_setup_sources_do_not_expand_the_generic_source_reader(self):
        delegation = self.fixture.fixture.fixture.fixture
        service = MemoryService(delegation.configuration)
        for relative in ('.env', 'LIFEOS/PULSE/PULSE.toml', 'LIFEOS/USER/WORK/config.yaml'):
            with self.subTest(relative=relative):
                result = service.native(delegation.context, 'read_source', {'path': str(self.root / relative)})
                self.assertFalse(result['ok'])
