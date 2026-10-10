# ABOUTME: Tests bounded owner-job output against real native memory retirement records.
# ABOUTME: Preserves reviewer limits and refuses oversized, stale, and restricted output delivery.
from dataclasses import replace
from datetime import datetime, timezone
import unittest

import test_memory_native as native_fixture


class MemoryJobOutputTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.scope = native_fixture.OWNER
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def test_current_output_above_reviewer_limit_is_delivered_exactly(self):
        content = 'Current synthetic owner output.\n' * 3000
        self.assertGreater(len(content), 65536)
        result = self.memory.filter_job_output(self.scope, content, self.timestamp)
        self.assertEqual(result, {'content': content, 'excluded': False})

    def test_reviewer_history_retains_its_character_limit(self):
        content = 'x' * 65536
        self.assertEqual(self.memory.filter_history(self.scope, content, self.timestamp)['content'], content)
        with self.assertRaisesRegex(ValueError, 'Invalid reviewer history input'):
            self.memory.filter_history(self.scope, content + 'x', self.timestamp)

    def test_output_limit_counts_utf8_bytes(self):
        with self.assertRaises(ValueError):
            self.memory.filter_job_output(self.scope, 'x' * (4 * 1024 * 1024 + 1), self.timestamp)
        with self.assertRaises(ValueError):
            self.memory.filter_job_output(self.scope, '\u00e9' * (2 * 1024 * 1024 + 1), self.timestamp)

    def test_retired_claim_after_reviewer_limit_withholds_complete_output(self):
        claim = 'Synthetic retired owner job output claim'
        saved = self.memory.remember(self.scope, category='principal', content=claim,
            title='', project='', request_id='synthetic-job-output-retirement')
        self.memory.forget(self.scope, saved['reference'], 'synthetic-job-output-forget')
        content = 'Current synthetic owner output.\n' * 3000 + claim
        result = self.memory.filter_job_output(self.scope, content, '2100-01-01T00:00:00Z')
        self.assertEqual(result, {'content': '', 'excluded': True})

    def test_restricted_grants_withhold_complete_output(self):
        content = 'Current synthetic owner output.\n' * 3000
        for scope in (replace(self.scope, write=()), replace(self.scope, read=('project',)),
                      replace(self.scope, projects=('lab',))):
            with self.subTest(scope=scope):
                self.assertEqual(self.memory.filter_job_output(scope, content, self.timestamp),
                    {'content': '', 'excluded': True})
