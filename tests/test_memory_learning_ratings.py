# ABOUTME: Characterizes native rating analysis and synthesis report publication.
# ABOUTME: Measures current source policy, native counts, and owner writer authority.
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
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
        self.rows = [self.row('Well done on synthetic verification', 8),
                     self.row('Synthetic code is too complex', 2)]
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
        self.assertIn('Success Patterns: 1', result.stdout)
        self.assertFalse(self.reports())

    def test_missing_context_cannot_publish_a_report(self):
        result = self.call('--all', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.reports())

    def test_private_rating_is_absent_from_native_counts_and_report(self):
        self.write(self.rows + [self.row('<private>Synthetic private rating is too complex</private>', 1)])
        result = self.call('--all')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Loaded 2 total ratings', result.stdout)
        self.assertNotIn('Synthetic private rating', ''.join(path.read_text() for path in self.reports()))

    def test_retired_rating_cannot_return_in_a_generated_report(self):
        marker = 'Synthetic retired rating is too complex'
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

    def test_extreme_numeric_rating_returns_a_refusal(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        row = self.row('Synthetic extreme rating')
        row['rating'] = 10 ** 400
        self.write([row])
        result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'learning_ratings', {
            'path': str(self.ratings), 'month': False, 'all': True, 'dry_run': False, 'request_id': 'extreme-rating'})
        self.assertFalse(result['ok'], result)
        self.assertFalse(self.reports())

    def test_original_native_period_modes_match_analysis_and_report_bytes(self):
        control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/LearningPatternSynthesis.ts'
        older = []
        for age in (20, 40):
            row = self.row('Synthetic older clean implementation', 7)
            row['timestamp'] = (datetime.now(timezone.utc) - timedelta(days=age)).isoformat()
            older.append(row)
        self.write(self.rows + older)
        for period in ((), ('--week',), ('--month',), ('--all',)):
            for dry in ((), ('--dry-run',)):
                with self.subTest(period=period, dry=dry):
                    for path in self.reports():
                        path.unlink()
                    managed = self.call(*period, *dry)
                    self.assertEqual(managed.returncode, 0, managed.stderr)
                    expected = {str(path.relative_to(self.synthesis)): path.read_bytes() for path in self.reports()}
                    for path in self.reports():
                        path.unlink()
                    env = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
                    original = subprocess.run(['bun', '--no-install', str(control), *period, *dry],
                        env=env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(original.returncode, 0, original.stderr)
                    self.assertEqual(managed.stderr + original.stderr, '')
                    self.assertEqual(managed.stdout, original.stdout)
                    self.assertEqual({str(path.relative_to(self.synthesis)): path.read_bytes()
                                      for path in self.reports()}, expected)

    def test_native_ignored_json_lines_remain_ignored(self):
        self.ratings.write_text(self.ratings.read_text() + 'not-json\nnull\n')
        result = self.call('--all', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Loaded 2 total ratings', result.stdout)

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_learning_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def previous(self):
        day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        month = datetime.now().astimezone().strftime('%Y-%m')
        path = self.synthesis / month / (day + '_all-time-patterns.md')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Synthetic previous rating report\n')
        return path, path.read_bytes()

    def test_later_source_authority_and_destination_changes_preserve_reports(self):
        baseline = self.fixture.configuration.load()
        for mode in ('source', 'authority', 'destination'):
            with self.subTest(mode=mode):
                self.fixture.configuration.update(lambda value: value.update(baseline))
                self.write(self.rows)
                path, before = self.previous()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['ok'], result.stdout)
                with self.fixture.fixture.memory._transaction():
                    pass
                expected = b'Synthetic later rating report edit\n' if mode == 'destination' else before
                self.assertEqual(path.read_bytes(), expected)

    def test_process_death_recovers_the_previous_report(self):
        path, before = self.previous()
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.assertNotEqual(path.read_bytes(), before)
        with self.fixture.fixture.memory._transaction():
            pass
        self.assertEqual(path.read_bytes(), before)
