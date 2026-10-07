# ABOUTME: Exercises native hypothesis derivation through current memory policy.
# ABOUTME: Verifies private inputs, current owner authority, and grouped publications.
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import re
import shutil
import sys
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryHypothesisTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.ratings = self.root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        self.ratings.parent.mkdir(parents=True, exist_ok=True)
        self.hypotheses = self.root / 'LIFEOS/MEMORY/WISDOM/FRAMES/_hypotheses'
        self.log = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/deriver.log'
        self.rows = [{'timestamp': datetime.now(timezone.utc).isoformat(), 'rating': 8,
            'session_id': 'synthetic-' + str(n), 'source': 'explicit', 'sentiment_summary': 'Well done on synthetic verification',
            'confidence': 1} for n in range(8)]
        self.write(self.rows)

    def write(self, rows):
        self.ratings.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def call(self, *args, context=True, original=False, inference=False):
        source = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) if original else self.root
        env = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'LIFEOS_DIR': str(self.root / 'LIFEOS'),
               'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        env.pop('LIFEOS_MEMORY_INTERNAL', None)
        env.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            env['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(source / 'LIFEOS/TOOLS/LearningPatternSynthesis.ts'),
            '--hypothesize', *([] if inference else ['--no-inference']), *args], env=env, capture_output=True, text=True, timeout=40)

    def notes(self):
        return list(self.hypotheses.glob('*.md')) if self.hypotheses.exists() else []

    def test_owner_emits_native_hypothesis_and_updates_same_note(self):
        first = self.call()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stderr, '')
        self.assertIn('emitted=1 updated=0', first.stdout)
        self.assertEqual(len(self.notes()), 1)
        note = self.notes()[0]
        self.assertIn('Recurring clean implementation pattern (8 signals, avg rating 8.0/10)', note.read_text())
        second = self.call()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('emitted=0 updated=1', second.stdout)
        self.assertEqual(self.notes(), [note])
        self.assertIn('updated in place', note.read_text())

    def test_missing_context_cannot_publish_notes_state_or_log(self):
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.notes())
        self.assertFalse((self.hypotheses / '.state.json').exists())
        self.assertFalse(self.log.exists())

    def test_private_ratings_cannot_create_a_hypothesis(self):
        self.write([dict(row, sentiment_summary='Well done <private>Synthetic private rating</private>') for row in self.rows])
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('emitted=0', result.stdout)
        self.assertFalse(self.notes())

    def test_retired_rating_pattern_cannot_return(self):
        marker = 'Well done on synthetic verification'
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='assistant', content='RULE: ' + marker,
            title='', project='', request_id='hypothesis-retire')
        self.assertEqual(saved['status'], 'committed', saved)
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'hypothesis-forget')['status'], 'committed')
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.notes())

    def test_revoked_account_cannot_read_or_publish(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call('--dry-run').returncode, 0)
        self.assertFalse(self.log.exists())

    def test_native_note_and_state_publications_have_private_permissions(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        for target in [*self.notes(), self.hypotheses / '.state.json', self.log]:
            with self.subTest(path=target.name):
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_read_only_owner_dry_run_creates_no_files(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        result = self.call('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('emitted=1', result.stdout)
        self.assertFalse(self.log.exists())
        self.assertFalse(self.hypotheses.exists())
        self.assertNotEqual(self.call().returncode, 0)

    def test_redirected_hypotheses_directory_cannot_write_foreign_notes(self):
        foreign = self.fixture.fixture.home / 'foreign-hypotheses'
        foreign.mkdir()
        self.hypotheses.parent.mkdir(parents=True, exist_ok=True)
        self.hypotheses.symlink_to(foreign, target_is_directory=True)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(list(foreign.iterdir()))

    def snapshot(self):
        paths = ([*self.hypotheses.rglob('*')] if self.hypotheses.exists() else []) + [self.log]
        return {str(path.relative_to(self.root)): path.read_text() for path in paths if path.is_file()}

    def normalized(self, value):
        return re.sub(r'20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9:.]+(?:Z|[+]00:00)', '<clock>', value)

    def test_original_native_creation_update_and_expiry_effects_match(self):
        for mode in ('create', 'update', 'expiry'):
            with self.subTest(mode=mode):
                if self.hypotheses.exists():
                    shutil.rmtree(self.hypotheses)
                if self.log.exists():
                    self.log.unlink()
                self.write(self.rows)
                if mode == 'update':
                    self.assertEqual(self.call().returncode, 0)
                elif mode == 'expiry':
                    self.hypotheses.mkdir(parents=True)
                    (self.hypotheses / '2000-01-01_synthetic.md').write_text(
                        '---\nstatus: hypothesis\nslug: synthetic\nexpires: 2000-01-02T00:00:00Z\n---\nSynthetic old hypothesis\n')
                    self.write([])
                before = self.snapshot()
                actual = self.call()
                self.assertEqual(actual.returncode, 0, actual.stderr)
                expected = self.snapshot()
                if self.hypotheses.exists():
                    shutil.rmtree(self.hypotheses)
                if self.log.exists():
                    self.log.unlink()
                for relative, content in before.items():
                    path = self.root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                original = self.call(original=True)
                self.assertEqual(original.returncode, 0, original.stderr)
                self.assertEqual(actual.stderr + original.stderr, '')
                self.assertEqual(actual.stdout, original.stdout)
                self.assertEqual({k: self.normalized(v) for k,v in self.snapshot().items()},
                                 {k: self.normalized(v) for k,v in expected.items()})

    def test_once_daily_publishes_one_stamp_and_keeps_later_run_unchanged(self):
        first = self.call('--once-daily')
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.snapshot()
        stamp = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/deriver-lastrun.date'
        self.assertEqual(stamp.stat().st_mode & 0o777, 0o600)
        second = self.call('--once-daily')
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('already ran', second.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_native_principal_name_and_private_settings_policy(self):
        settings = self.root / 'settings.json'
        settings.write_text(json.dumps({'principal': {'name': 'SyntheticOperator'}}))
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SyntheticOperator reviews', self.notes()[0].read_text())
        settings.write_text(json.dumps({'principal': {'name': '<private>SyntheticSecret</private>'}}))
        before = self.snapshot()
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_observability_intake_matches_native_public_missing_harness_behavior(self):
        self.write([])
        stream = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-failures.jsonl'
        stream.parent.mkdir(parents=True, exist_ok=True)
        row = {'timestamp': datetime.now(timezone.utc).isoformat(), 'event': 'tool_failure',
               'tool_name': 'terminal', 'error': 'Synthetic recurrence failure'}
        stream.write_text(''.join(json.dumps(row) + '\n' for _ in range(12)))
        actual = self.call(inference=True)
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.assertIn('emitted=1', actual.stdout)
        self.assertIn('hook-replay harness not present', self.log.read_text())
        expected = self.snapshot()
        shutil.rmtree(self.hypotheses)
        self.log.unlink()
        original = self.call(original=True, inference=True)
        self.assertEqual(original.returncode, 0, original.stderr)
        self.assertEqual(actual.stdout, original.stdout)
        self.assertEqual({k: self.normalized(v) for k,v in self.snapshot().items()},
                         {k: self.normalized(v) for k,v in expected.items()})

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_hypotheses_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def test_later_source_authority_or_note_change_preserves_data(self):
        self.assertEqual(self.call().returncode, 0)
        note = self.notes()[0]
        for mode in ('source', 'destination', 'authority'):
            with self.subTest(mode=mode):
                self.write(self.rows)
                before = self.snapshot()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertFalse(json.loads(result.stdout)['ok'])
                expected = dict(before)
                if mode == 'destination':
                    expected[str(note.relative_to(self.root))] = 'Synthetic later hypothesis edit\n'
                self.assertEqual(self.snapshot(), expected)

    def test_grouped_publication_recovers_after_process_death(self):
        self.assertEqual(self.call().returncode, 0)
        before = self.snapshot()
        self.write([dict(row, rating=7) for row in self.rows])
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73, result.stdout)
        self.assertNotEqual(self.snapshot(), before)
        with self.fixture.fixture.memory._transaction():
            pass
        self.assertEqual(self.snapshot(), before)

    def test_expired_live_slug_can_create_a_current_hypothesis(self):
        self.assertEqual(self.call().returncode, 0)
        note = self.notes()[0]
        content = re.sub(r'^expires:.*$', 'expires: 2000-01-01T00:00:00Z', note.read_text(), flags=re.MULTILINE)
        note.write_text(content)
        (self.hypotheses / '.state.json').unlink()
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('expired=1 emitted=1', result.stdout)
        self.assertEqual(len(self.notes()), 1)
        self.assertIn('status: hypothesis', self.notes()[0].read_text())
        archived = self.hypotheses / '_archive' / note.name
        self.assertIn('status: expired', archived.read_text())

    def test_snake_case_identity_user_directory_cannot_redirect_reads(self):
        foreign = self.fixture.fixture.home / 'foreign-user'
        foreign.mkdir()
        config = self.root / 'LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml'
        config.write_text('[principal]\nname = "SyntheticOperator"\ntimezone = "UTC"\n'
            '[da]\nname = "SyntheticAssistant"\n[da.voices.main]\nvoice_id = ""\n'
            '[paths]\nuser_dir = ' + json.dumps(str(foreign)) + '\n')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.notes())

    def test_same_request_returns_receipt_without_another_derivation(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        service = MemoryService(self.fixture.configuration)
        arguments = {'path': str(self.ratings), 'window': 7, 'dry_run': False, 'no_inference': True,
                     'once_daily': False, 'request_id': 'hypothesis-retry'}
        first = service.native(self.fixture.context, 'learning_hypotheses', arguments)
        self.assertTrue(first['ok'], first)
        before = self.snapshot()
        second = service.native(self.fixture.context, 'learning_hypotheses', arguments)
        self.assertTrue(second['ok'], second)
        self.assertEqual(second['receipt'], first['receipt'])
        self.assertEqual(self.snapshot(), before)

    def test_derivation_cannot_remove_a_registered_fact_from_a_note(self):
        self.assertEqual(self.call().returncode, 0)
        memory = self.fixture.fixture.memory
        marker = 'RULE: Synthetic retained hypothesis fact'
        saved = memory.remember(OWNER, category='assistant', content=marker,
            title='', project='', request_id='hypothesis-registered')
        self.assertEqual(saved['status'], 'committed', saved)
        note = self.notes()[0]
        note.write_text(note.read_text() + '\n' + marker + '\n')
        with memory._transaction() as connection:
            connection.execute('UPDATE records SET path=?, position=? WHERE id=?',
                (str(note.relative_to(self.root)), note.read_text().index(marker), saved['reference']['id']))
        self.assertEqual(memory.get(OWNER, saved['reference'])['content'], marker)
        before = self.snapshot()
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(memory.get(OWNER, saved['reference'])['content'], marker)
