# ABOUTME: Exercises native Wisdom classification, frame loading, and cross-frame synthesis.
# ABOUTME: Measures current source admission and fixed report publication with synthetic frames.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryWisdomReaderTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.wisdom = self.root / 'LIFEOS/MEMORY/WISDOM'
        self.frames = self.wisdom / 'FRAMES'
        self.frames.mkdir(parents=True, exist_ok=True)
        self.frame = self.frames / 'communication.md'
        self.frame.write_text(self.body('Synthetic concrete verification principle'))
        (self.frames / 'development.md').write_text(self.body('Synthetic concrete verification principle'))
        self.principles = self.wisdom / 'PRINCIPLES/verified.md'
        self.health = self.wisdom / 'META/frame-health.md'

    def body(self, principle):
        return '# Synthetic frame\n## Meta\n- **Confidence:** 70%\n- **Observation Count:** 12\n' + \
            '- **Last Crystallized:** 2026-10-01\n\n## Core Principles\n### ' + principle + ' [CRYSTAL]\n'

    def environment(self, context):
        env = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'LIFEOS_DIR': str(self.root / 'LIFEOS'),
               'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        env.pop('LIFEOS_MEMORY_INTERNAL', None)
        env.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            env['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return env

    def call(self, *args, context=True, tool='WisdomCrossFrameSynthesizer.ts'):
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS' / tool), *args],
            capture_output=True, text=True, env=self.environment(context), timeout=40)

    def library(self, function, *args, context=True, original=False):
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m[process.argv[2]](...JSON.parse(process.argv[3]))));'
        tool = (Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) if original else self.root) / 'LIFEOS/TOOLS/WisdomDomainClassifier.ts'
        return subprocess.run(['bun', '--no-install', '-e', program,
            str(tool), function, json.dumps(args)],
            capture_output=True, text=True, env=self.environment(context), timeout=40)

    def test_owner_dry_synthesis_preserves_native_principles_and_counts(self):
        result = self.call('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Synthetic concrete verification principle', result.stdout)
        self.assertIn('**Frames Analyzed:** 2', result.stdout)
        self.assertFalse(self.principles.exists())
        self.assertFalse(self.health.exists())

    def test_missing_context_refuses_before_report_publication(self):
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic concrete verification principle', result.stdout)
        self.assertFalse(self.principles.exists())
        self.assertFalse(self.health.exists())

    def test_private_frame_is_absent_from_native_loading_and_synthesis(self):
        self.frame.write_text(self.body('<private>Synthetic private Wisdom principle</private>'))
        for result in (self.library('loadRelevantFrames', 'format response'), self.call('--dry-run')):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertNotIn('Synthetic private Wisdom principle', result.stdout)
        self.assertEqual(json.loads(self.library('loadRelevantFrames', 'format response').stdout), [])

    def test_retired_frame_is_absent_from_current_native_loading(self):
        marker = 'Synthetic retired Wisdom principle'
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='assistant', content='RULE: ' + marker,
            title='', project='', request_id='wisdom-reader-retired')
        self.assertEqual(saved['status'], 'committed', saved)
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'wisdom-reader-forget')['status'], 'committed')
        self.frame.write_text(self.body(marker))
        result = self.library('loadRelevantFrames', 'format response')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(marker, result.stdout)
        self.assertEqual(json.loads(result.stdout), [])

    def test_revoked_account_refuses_loading_and_synthesis(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        for result in (self.library('listFrames'), self.call('--dry-run')):
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Synthetic concrete verification principle', result.stdout)

    def test_read_only_owner_can_read_but_cannot_publish_reports(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertEqual(self.call('--dry-run').returncode, 0)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.principles.exists())
        self.assertFalse(self.health.exists())

    def test_managed_reports_have_private_permissions(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.principles.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.health.stat().st_mode & 0o777, 0o600)

    def test_redirected_frame_refuses_without_loading_foreign_content(self):
        foreign = self.fixture.fixture.home / 'foreign-wisdom-reader.md'
        foreign.write_text(self.body('Synthetic foreign Wisdom principle'))
        self.frame.unlink()
        self.frame.symlink_to(foreign)
        for result in (self.library('listFrames'), self.call('--dry-run')):
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Synthetic foreign Wisdom principle', result.stdout)

    def test_original_native_classification_loading_and_listing_match(self):
        for function, args in (('listFrames', ()), ('classifyDomains', ('format response code build',)),
                               ('loadRelevantFrames', ('format response code build', 2))):
            with self.subTest(function=function):
                managed = self.library(function, *args)
                original = self.library(function, *args, original=True)
                self.assertEqual(managed.returncode, 0, managed.stderr)
                self.assertEqual(original.returncode, 0, original.stderr)
                self.assertEqual(managed.stderr + original.stderr, '')
                self.assertEqual(json.loads(managed.stdout), json.loads(original.stdout))

    def test_original_native_report_bytes_and_stdout_match_all_modes(self):
        control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/WisdomCrossFrameSynthesizer.ts'
        for args in ((), ('--dry-run',), ('--health',), ('--health', '--dry-run')):
            with self.subTest(args=args):
                for path in (self.principles, self.health):
                    path.unlink(missing_ok=True)
                managed = self.call(*args)
                self.assertEqual(managed.returncode, 0, managed.stderr)
                expected = [path.read_bytes() if path.exists() else None for path in (self.principles, self.health)]
                for path in (self.principles, self.health):
                    path.unlink(missing_ok=True)
                original = subprocess.run(['bun', '--no-install', str(control), *args],
                    env=self.environment(True), capture_output=True, text=True, timeout=30)
                self.assertEqual(original.returncode, 0, original.stderr)
                self.assertEqual(managed.stderr + original.stderr, '')
                self.assertEqual(managed.stdout, original.stdout)
                self.assertEqual([path.read_bytes() if path.exists() else None
                                  for path in (self.principles, self.health)], expected)

    def previous(self):
        for path, content in ((self.principles, 'Synthetic previous principles\n'),
                              (self.health, 'Synthetic previous frame health\n')):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return self.principles.read_bytes(), self.health.read_bytes()

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_wisdom_synthesis_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True,
            env=self.environment(True), timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def test_later_source_authority_and_report_changes_preserve_outputs(self):
        baseline = self.fixture.configuration.load()
        for mode in ('source', 'authority', 'destination', 'frames-authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.update(lambda value: value.update(baseline))
                before = self.previous()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['ok'], result.stdout)
                expected = (b'Synthetic later principles edit\n', before[1]) if mode == 'destination' else before
                with self.fixture.fixture.memory._transaction():
                    pass
                self.assertEqual((self.principles.read_bytes(), self.health.read_bytes()), expected)

    def test_process_death_recovers_the_previous_report_pair(self):
        before = self.previous()
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.assertNotEqual(self.principles.read_bytes(), before[0])
        self.assertEqual(self.health.read_bytes(), before[1])
        with self.fixture.fixture.memory._transaction():
            pass
        self.assertEqual((self.principles.read_bytes(), self.health.read_bytes()), before)
