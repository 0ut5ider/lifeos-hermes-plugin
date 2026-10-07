# ABOUTME: Characterizes native interview inputs, completion state, and verdict publication.
# ABOUTME: Uses synthetic sources to check current owner authority and fixed destinations.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_state_evidence as evidence_fixture


class MemoryInterviewDueTests(unittest.TestCase):
    def setUp(self):
        self.fixture = evidence_fixture.MemoryStateEvidenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.cache = self.root / 'LIFEOS/USER/CACHE/interview-due.json'
        self.state = self.fixture.source('LIFEOS/MEMORY/STATE/interview.json',
            {'last_interview': self.fixture.day + 'T00:00:00Z', 'marked_by': 'synthetic-interview'})
        self.fixture.fixture.source('LIFEOS/USER/TELOS/CURRENT_STATE/HEALTH.md',
            '# Synthetic current health\n', reviewed='2026-09-01')

    def call(self, *args, context=True):
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/InterviewDue.ts'), *args],
            env=self.fixture.fixture.environment(context=context), capture_output=True, text=True, timeout=30)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def library(self, function, *args, context=True):
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m[process.argv[2]](...JSON.parse(process.argv[3]))));'
        return subprocess.run(['bun', '--no-install', '-e', program, str(self.root / 'LIFEOS/TOOLS/InterviewDue.ts'),
            function, json.dumps(args)], env=self.fixture.fixture.environment(context=context),
            capture_output=True, text=True, timeout=30)

    def previous(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text('{"synthetic_previous":"preserved"}')
        return self.cache.read_bytes()

    def read_only(self):
        self.fixture.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))

    def test_owner_verdict_preserves_native_fields_and_current_cadence(self):
        verdict = json.loads(self.successful().stdout)
        self.assertEqual(verdict['schema'], 1)
        self.assertEqual(verdict['inputs']['days_since_last_interview'], 0)
        self.assertEqual(verdict, json.loads(self.cache.read_text()))
        self.assertIn('freshness and cadence', ' '.join(verdict['reasons']))

    def test_owner_refresh_and_mark_done_preserve_native_completion_fields(self):
        verdict = json.loads(self.successful('--refresh', '--mark-done').stdout)
        self.assertEqual(verdict['inputs']['days_since_last_interview'], 0)
        self.assertEqual(json.loads(self.state.read_text())['marked_by'], 'interview-skill')
        self.assertTrue(self.fixture.cache.exists())
        self.assertTrue((self.root / 'LIFEOS/USER/CACHE/freshness.json').exists())

    def test_read_only_owner_preserves_state_and_verdict_cache(self):
        before = self.previous()
        state = self.state.read_bytes()
        self.read_only()
        verdict = json.loads(self.successful('--mark-done').stdout)
        self.assertEqual(verdict['schema'], 1)
        self.assertEqual(self.state.read_bytes(), state)
        self.assertEqual(self.cache.read_bytes(), before)

    def test_missing_context_cannot_mark_completion_before_refused_read(self):
        state = self.state.read_bytes()
        result = self.call('--mark-done', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state.read_bytes(), state)
        self.assertFalse(self.cache.exists())

    def test_missing_context_cannot_read_completion_inputs(self):
        result = self.library('buildInputs', None, context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('days_since_last_interview', result.stdout)

    def test_foreign_completion_source_refuses_without_using_its_date(self):
        foreign = self.fixture.fixture.fixture.fixture.home / 'foreign-interview.json'
        foreign.write_text('{"last_interview":"2026-01-01T00:00:00Z"}')
        self.state.unlink(); self.state.symlink_to(foreign)
        result = self.library('buildInputs', None)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('days_since_last_interview', result.stdout)

    def test_foreign_completion_source_is_not_replaced_by_mark_done(self):
        foreign = self.fixture.fixture.fixture.fixture.home / 'foreign-interview.json'
        foreign.write_text('{"last_interview":"2026-01-01T00:00:00Z"}')
        self.state.unlink(); self.state.symlink_to(foreign)
        result = self.library('markInterviewDone')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), False)
        self.assertTrue(self.state.is_symlink())
        self.assertEqual(foreign.read_text(), '{"last_interview":"2026-01-01T00:00:00Z"}')

    def test_completion_and_cache_publications_have_private_permissions(self):
        self.successful('--mark-done')
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)

    def test_library_writers_cannot_publish_to_an_arbitrary_path(self):
        foreign = self.fixture.fixture.fixture.fixture.home / 'foreign-verdict.json'
        verdict = json.loads(self.successful().stdout)
        result = self.library('writeVerdictCache', verdict, str(foreign))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), False)
        self.assertFalse(foreign.exists())

    def test_completion_library_cannot_publish_to_an_arbitrary_path(self):
        foreign = self.fixture.fixture.fixture.fixture.home / 'foreign-completion.json'
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m.markInterviewDone(new Date(),process.argv[2])));'
        result = subprocess.run(['bun', '--no-install', '-e', program,
            str(self.root / 'LIFEOS/TOOLS/InterviewDue.ts'), str(foreign)],
            env=self.fixture.fixture.environment(), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), False)
        self.assertFalse(foreign.exists())

    def test_revoked_owner_cannot_mark_completion(self):
        state = self.state.read_bytes()
        self.fixture.fixture.fixture.configuration.update(lambda c: c['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call('--mark-done').returncode, 0)
        self.assertEqual(self.state.read_bytes(), state)

    def process(self, mode, operation):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_interview_process.py')),
            str(self.fixture.fixture.fixture.configuration.path), mode, operation],
            env=self.fixture.fixture.environment(), capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def test_post_render_source_changes_preserve_later_completion_state(self):
        initial = self.state.read_bytes()
        for mode in ('source', 'source_excluded', 'source_large'):
            for operation in ('interview_due_mark', 'interview_due_cache_write'):
                with self.subTest(mode=mode, operation=operation):
                    self.state.write_bytes(initial)
                    before = self.previous()
                    result = self.process(mode, operation)
                    self.assertEqual(result.returncode, 0)
                    self.assertFalse(json.loads(result.stdout)['ok'])
                    with self.fixture.fixture.memory._transaction():
                        self.assertEqual(self.cache.read_bytes(), before)
                    self.assertIn('synthetic_later', json.loads(self.state.read_text()))

    def test_post_render_revocation_preserves_completion_and_cache(self):
        before = self.previous()
        state = self.state.read_bytes()
        result = self.process('authority', 'interview_due_mark')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        with self.fixture.fixture.memory._transaction():
            self.assertEqual(self.state.read_bytes(), state)
            self.assertEqual(self.cache.read_bytes(), before)

    def test_interrupted_completion_and_verdict_recover_original_bytes(self):
        for operation in ('interview_due_mark', 'interview_due_cache_write'):
            with self.subTest(operation=operation):
                before = self.previous()
                state = self.state.read_bytes()
                result = self.process('interrupt', operation)
                self.assertEqual(result.returncode, 73)
                self.assertTrue(self.fixture.fixture.memory.transaction.journal.exists())
                with self.fixture.fixture.memory._transaction():
                    self.assertEqual(self.cache.read_bytes(), before)
                    self.assertEqual(self.state.read_bytes(), state)
                self.assertFalse(self.fixture.fixture.memory.transaction.journal.exists())

    def test_completion_and_verdict_cannot_alias_the_registry(self):
        self.fixture.fixture.fixture.fixture.remember('Synthetic interview registry guard', 'interview-alias')
        for path, function in ((self.state, 'markInterviewDone'), (self.cache, 'writeVerdictCache')):
            with self.subTest(path=path):
                if path.exists():
                    path.unlink()
                path.parent.mkdir(parents=True, exist_ok=True)
                os.link(self.fixture.fixture.memory.database, path)
                args = () if function == 'markInterviewDone' else ({'schema': 1, 'computed_at': '2026-10-04T00:00:00Z'},)
                result = self.library(function, *args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), False)
                self.assertTrue(path.samefile(self.fixture.fixture.memory.database))
                path.unlink()

    def test_inputs_match_pinned_original_native_implementation(self):
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m.buildInputs(null,new Date(process.argv[2]))));'
        now = self.fixture.day + 'T12:00:00Z'
        original = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/InterviewDue.ts'
        outputs = []
        for module, context in ((self.root / 'LIFEOS/TOOLS/InterviewDue.ts', True), (original, False)):
            result = subprocess.run(['bun', '--no-install', '-e', program, str(module), now],
                env=self.fixture.fixture.environment(context=context), capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            outputs.append(json.loads(result.stdout))
        self.assertEqual(outputs[0], outputs[1])

    def test_post_render_read_change_refuses_delivery(self):
        for mode in ('source', 'authority'):
            with self.subTest(mode=mode):
                result = self.process(mode, 'interview_due_inputs')
                self.assertEqual(result.returncode, 0)
                self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertNotIn('days_since_last_interview', result.stdout)
                self.assertFalse(self.cache.exists())

    def test_supplied_verdict_cannot_publish_forged_reasons(self):
        before = self.previous()
        verdict = {'schema': 1, 'computed_at': self.fixture.day + 'T00:00:00Z', 'due': True,
                   'headline': 'Synthetic forged verdict', 'reasons': ['Synthetic forged reason'], 'inputs': {}}
        result = self.library('writeVerdictCache', verdict)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), False)
        with self.fixture.fixture.memory._transaction():
            self.assertEqual(self.cache.read_bytes(), before)

    def test_later_edit_to_an_already_excluded_completion_state_is_preserved(self):
        self.state.write_text(json.dumps({'last_interview': self.fixture.day + 'T00:00:00Z',
                                         'note': '<private>Synthetic excluded completion note</private>'}))
        result = self.process('source', 'interview_due_mark')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        with self.fixture.fixture.memory._transaction():
            self.assertIn('synthetic_later', json.loads(self.state.read_text()))
