# ABOUTME: Exercises native Knowledge distillation against governed synthetic notes.
# ABOUTME: Checks gather and status admission before any synthesis or publication.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import shutil
import unittest

import test_memory_delegation as delegation_fixture
import test_memory_native as native_fixture


class MemoryDistillTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.configuration = self.fixture.configuration
        self.native = self.fixture.fixture.memory
        self.saved = self.fixture.fixture.remember('Synthetic current distill marker', 'distill-note')
        self.assertEqual(self.saved['status'], 'committed')

    def call(self, *arguments, context=True):
        environment = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        environment.pop('LIFEOS_DIR', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/KnowledgeDistill.ts'),
            *arguments], capture_output=True, text=True, env=environment, timeout=40)

    def gather(self):
        result = self.call('gather', '--days', '36500', '--limit', '100')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_owner_gather_preserves_native_current_candidate(self):
        value = self.gather()
        self.assertEqual(value['scanned'], 1)
        self.assertEqual(len(value['candidates']), 1)
        self.assertIn('Synthetic current distill marker', value['candidates'][0]['summary'])

    def test_missing_context_refuses_gather_and_status(self):
        for args in [('gather', '--days', '36500'), ('status',)]:
            with self.subTest(args=args):
                result = self.call(*args, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic current distill marker', result.stdout)
                self.assertNotIn('surfaced_slugs', result.stdout)

    def test_forgotten_note_is_excluded_from_gather(self):
        self.native.forget(native_fixture.OWNER, self.saved['reference'], 'distill-forget')
        value = self.gather()
        self.assertEqual(value['scanned'], 0)
        self.assertEqual(value['candidates'], [])
        self.assertNotIn('Synthetic current distill marker', json.dumps(value))

    def test_unregistered_note_is_excluded_from_gather(self):
        path = self.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research/unregistered.md'
        path.write_text('---\ntitle: Synthetic unknown note\ncreated: 2026-10-04\n---\nSynthetic unknown distill marker\n')
        value = self.gather()
        self.assertEqual(value['scanned'], 1)
        self.assertNotIn('Synthetic unknown distill marker', json.dumps(value))

    def test_revoked_account_refuses_gather(self):
        self.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.call('gather', '--days', '36500')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current distill marker', result.stdout)

    def test_restricted_reader_refuses_unclassified_gather(self):
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(read=['project'], projects=['lab']))
        result = self.call('gather', '--days', '36500')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current distill marker', result.stdout)

    def test_owner_status_preserves_native_tracking_counts_and_configuration(self):
        state = self.root / 'LIFEOS/MEMORY/STATE/distill.json'
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({'schema_version': 1, 'surfaced_slugs': {'synthetic-note': '2026-10-04'},
            'item_hashes': {'synthetic-hash': '2026-10-04'}, 'last_run': '2026-10-04'}))
        config = self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/Cortex/DistillConfig.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'maxDigestItems': 4, 'windowDays': 10}))
        result = self.call('status')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'last_run': '2026-10-04', 'surfaced_slugs': 1,
            'item_hashes': 1, 'config': {'maxIssues': 5, 'maxUpgrades': 5, 'maxDigestItems': 4, 'windowDays': 10}})

    def test_foreign_config_path_refuses_status(self):
        config = self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/Cortex/DistillConfig.json'
        config.parent.mkdir(parents=True)
        foreign = self.fixture.fixture.home / 'foreign-distill-config.json'
        before = b'{"contentRepo":"synthetic/foreign"}\n'
        foreign.write_bytes(before)
        config.symlink_to(foreign)
        result = self.call('status')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('synthetic/foreign', result.stdout)
        self.assertEqual(foreign.read_bytes(), before)

    def test_escaped_private_config_is_refused_before_readback(self):
        config = self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/Cortex/DistillConfig.json'
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'contentLabel': '<private>Synthetic hidden label.</private>'})
            .replace('<', '\\u003c').replace('>', '\\u003e'))
        result = self.call('status')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic hidden label', result.stdout)

    def test_original_native_gather_matches_selected_owner_fields(self):
        before = self.gather()
        tools = self.root / 'LIFEOS/TOOLS'
        source = tools.resolve()
        tools.unlink()
        tools.mkdir()
        for path in source.iterdir():
            if path.name != 'KnowledgeDistill.ts':
                (tools / path.name).symlink_to(path)
        control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/KnowledgeDistill.ts'
        shutil.copyfile(control, tools / 'KnowledgeDistill.ts')
        self.assertEqual(self.gather(), before)

    def test_unmanaged_native_reader_retains_original_output(self):
        before = self.gather()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertEqual(self.gather(), before)
