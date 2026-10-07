# ABOUTME: Characterizes native interview inputs, completion state, and verdict publication.
# ABOUTME: Uses synthetic sources to check current owner authority and fixed destinations.
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import unittest

from test_memory_state_evidence import MemoryStateEvidenceTests


class MemoryInterviewDueTests(unittest.TestCase):
    def setUp(self):
        self.fixture = MemoryStateEvidenceTests()
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
        foreign = self.fixture.fixture.fixture.fixture.fixture.home / 'foreign-completion.json'
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
