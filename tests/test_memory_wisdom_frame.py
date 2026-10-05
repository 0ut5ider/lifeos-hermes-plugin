# ABOUTME: Characterizes native Wisdom frame updates and current owner admission.
# ABOUTME: Uses real native programs with synthetic frame sources and observations.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryWisdomFrameTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.frames = self.root / 'LIFEOS/MEMORY/WISDOM/FRAMES'
        self.frames.mkdir(parents=True, exist_ok=True)
        self.path = self.frames / 'communication.md'

    def call(self, observation='Synthetic current observation', kind='evolution', *, context=True, domain='communication'):
        env = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'LIFEOS_DIR': str(self.root / 'LIFEOS'),
               'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        env.pop('LIFEOS_MEMORY_INTERNAL', None)
        env.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            env['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/WisdomFrameUpdater.ts'),
            '--domain', domain, '--observation', observation, '--type', kind], env=env,
            capture_output=True, text=True, timeout=40)

    def existing(self, body='Synthetic retained observation'):
        self.path.write_text('# Frame: Communication Domain\n\n## Meta\n- **Confidence:** 50%\n'
            '- **Observation Count:** 1\n- **Last Crystallized:** 2026-10-01\n\n'
            '## Core Principles\n\n## Contextual Rules\n\n## Predictive Model\n'
            '\n## Anti-Patterns\n\n## Evolution Log\n- 2026-10-01: ' + body + '\n')
        return self.path.read_bytes()

    def test_owner_preserves_native_update_types_and_messages(self):
        for kind in ('evolution', 'principle', 'contextual-rule', 'prediction', 'anti-pattern'):
            with self.subTest(kind=kind):
                self.existing()
                result = self.call(kind=kind)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertIn('Synthetic current observation', self.path.read_text())
                self.assertIn('**Observation Count:** 2', self.path.read_text())
                self.assertIn('Updated "communication" frame', json.loads(result.stdout)['message'])

    def test_managed_publication_has_private_permissions(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_missing_context_preserves_the_previous_frame(self):
        before = self.existing()
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_revoked_account_preserves_the_previous_frame(self):
        before = self.existing()
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_read_only_owner_preserves_the_previous_frame(self):
        before = self.existing()
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_private_observation_is_refused_before_publication(self):
        before = self.existing()
        result = self.call('<private>Synthetic private wisdom observation</private>')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn('Synthetic private wisdom observation', result.stdout)

    def test_retired_observation_cannot_return_through_frame_update(self):
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='assistant', content='RULE: Synthetic retired wisdom observation',
            title='', project='', request_id='wisdom-retired')
        self.assertEqual(saved['status'], 'committed', saved)
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'wisdom-forget')['status'], 'committed')
        before = self.existing()
        result = self.call('Synthetic retired wisdom observation')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_redirected_frame_does_not_change_the_foreign_file(self):
        foreign = self.fixture.fixture.home / 'foreign-wisdom.md'
        foreign.write_text('Synthetic foreign frame\n')
        self.path.symlink_to(foreign)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(foreign.read_text(), 'Synthetic foreign frame\n')

    def test_retirement_refuses_a_previous_receipt_after_frame_removal(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        memory = self.fixture.fixture.memory
        marker = 'Synthetic wisdom receipt retirement'
        saved = memory.remember(OWNER, category='assistant', content='RULE: ' + marker,
            title='', project='', request_id='wisdom-receipt-fact')
        self.assertEqual(saved['status'], 'committed', saved)
        arguments = {'domain': 'communication', 'observation': marker, 'type': 'evolution',
                     'path': str(self.path), 'request_id': 'wisdom-receipt'}
        service = MemoryService(self.fixture.configuration)
        self.assertTrue(service.native(self.fixture.context, 'wisdom_frame_update', arguments)['ok'])
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'wisdom-receipt-forget')['status'], 'committed')
        self.path.unlink()
        result = service.native(self.fixture.context, 'wisdom_frame_update', arguments)
        self.assertFalse(result['ok'], result)
        self.assertNotIn(marker, json.dumps(result))

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_wisdom_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def test_later_source_and_authority_changes_refuse_publication(self):
        baseline = self.fixture.configuration.load()
        for mode in ('source', 'private', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.update(lambda value: value.update(baseline))
                before = self.existing()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['ok'], result.stdout)
                expected = (b'Synthetic later wisdom edit\n' if mode == 'source' else
                    b'<private>Synthetic later private wisdom edit</private>\n' if mode == 'private' else before)
                with self.fixture.fixture.memory._transaction():
                    pass
                self.assertEqual(self.path.read_bytes(), expected)

    def test_process_death_recovers_the_previous_frame(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                if self.path.exists():
                    self.path.unlink()
                before = self.existing() if existing else None
                self.assertEqual(self.process('interrupt').returncode, 73)
                self.assertIn('Synthetic interrupted wisdom observation', self.path.read_text())
                with self.fixture.fixture.memory._transaction():
                    pass
                self.assertEqual(self.path.read_bytes() if self.path.exists() else None, before)

    def test_original_native_transformations_match_all_update_types(self):
        control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/WisdomFrameUpdater.ts'
        for kind in ('evolution', 'principle', 'contextual-rule', 'prediction', 'anti-pattern'):
            for existing in (False, True):
                with self.subTest(kind=kind, existing=existing):
                    if self.path.exists():
                        self.path.unlink()
                    if existing:
                        self.existing()
                    managed = self.call(kind=kind)
                    self.assertEqual(managed.returncode, 0, managed.stderr)
                    expected = self.path.read_bytes()
                    self.path.unlink()
                    if existing:
                        self.existing()
                    env = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'LIFEOS_DIR': str(self.root / 'LIFEOS')}
                    original = subprocess.run(['bun', '--no-install', str(control), '--domain', 'communication',
                        '--observation', 'Synthetic current observation', '--type', kind],
                        env=env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(original.returncode, 0, original.stderr)
                    self.assertEqual(original.stderr, '')
                    self.assertEqual(self.path.read_bytes(), expected)
                    self.assertEqual(json.loads(original.stdout), json.loads(managed.stdout))
