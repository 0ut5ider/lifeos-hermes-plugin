# ABOUTME: Characterizes native rating analysis and synthesis report publication.
# ABOUTME: Measures current source policy, native counts, and owner writer authority.
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryLearningRatingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.ratings = self.root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        self.ratings.parent.mkdir(parents=True, exist_ok=True)
        self.synthesis = self.root / 'LIFEOS/MEMORY/LEARNING/SYNTHESIS'
        self.rows = [self.row('Great job on synthetic verification', 8),
                     self.row('Synthetic code is too complicated', 2)]
        self.write(self.rows)

    def row(self, summary, rating=8):
        return {'timestamp': datetime.now(timezone.utc).isoformat(), 'rating': rating,
                'session_id': 'synthetic-rating-session', 'source': 'explicit',
                'sentiment_summary': summary, 'confidence': 0.9}

    def write(self, rows):
        self.ratings.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')

    def call(self, *args, context=True):
        env = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        env.pop('LIFEOS_MEMORY_INTERNAL', None)
        env.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            env['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/LearningPatternSynthesis.ts'),
            *args], capture_output=True, text=True, env=env, timeout=40)

    def reports(self):
        return list(self.synthesis.rglob('*.md')) if self.synthesis.exists() else []

    def test_owner_analysis_preserves_native_counts_and_patterns(self):
        result = self.call('--all', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Loaded 2 total ratings', result.stdout)
        self.assertIn('Average Rating: 5.0/10', result.stdout)
        self.assertIn('Over-engineering', result.stdout)
        self.assertFalse(self.reports())

    def test_missing_context_cannot_publish_a_report(self):
        result = self.call('--all', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.reports())

    def test_private_rating_is_absent_from_native_counts_and_report(self):
        self.write(self.rows + [self.row('<private>Synthetic private rating is too complicated</private>', 1)])
        result = self.call('--all')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Loaded 2 total ratings', result.stdout)
        self.assertNotIn('Synthetic private rating', ''.join(path.read_text() for path in self.reports()))

    def test_retired_rating_cannot_return_in_a_generated_report(self):
        marker = 'Synthetic retired rating is too complicated'
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='assistant', content='RULE: ' + marker,
            title='', project='', request_id='rating-retired')
        self.assertEqual(saved['status'], 'committed', saved)
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'rating-forget')['status'], 'committed')
        self.write([self.row('Great job on synthetic verification'), self.row(marker, 1)])
        result = self.call('--all')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Loaded 1 total ratings', result.stdout)
        self.assertNotIn(marker, ''.join(path.read_text() for path in self.reports()))

    def test_revoked_account_cannot_analyze_ratings(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call('--all', '--dry-run').returncode, 0)

    def test_read_only_owner_can_analyze_but_cannot_publish(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertEqual(self.call('--all', '--dry-run').returncode, 0)
        self.assertNotEqual(self.call('--all').returncode, 0)
        self.assertFalse(self.reports())

    def test_native_report_has_private_permissions(self):
        result = self.call('--all')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.reports()), 1)
        self.assertEqual(self.reports()[0].stat().st_mode & 0o777, 0o600)

    def test_redirected_ratings_refuse_without_generating_foreign_examples(self):
        foreign = self.fixture.fixture.home / 'foreign-ratings.jsonl'
        foreign.write_bytes(self.ratings.read_bytes())
        self.ratings.unlink()
        self.ratings.symlink_to(foreign)
        self.assertNotEqual(self.call('--all').returncode, 0)
        self.assertFalse(self.reports())
