# ABOUTME: Checks derivative source and authority changes before tracking publication.
# ABOUTME: Verifies actual interruption restores previous state or removes a new destination.
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_derived_sync as sync_fixture
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryDerivedSyncConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = sync_fixture.MemoryDerivedSyncTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.fixture.fixture.configuration

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_derived_sync_process.py')),
            str(self.configuration.path), mode], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.stderr, '')
        return result

    def previous(self):
        self.fixture.state.parent.mkdir(parents=True, exist_ok=True)
        self.fixture.log.parent.mkdir(parents=True, exist_ok=True)
        self.fixture.state.write_text('{"fileHashes":{},"lastRun":"2026-10-04T00:00:00.000Z"}\n')
        self.fixture.log.write_text('{"ts":"2026-10-04T00:00:00.000Z","changed":[],"actions":[],"dryRun":false}\n')
        return self.fixture.state.read_bytes(), self.fixture.log.read_bytes()

    def test_post_render_changes_refuse_and_preserve_later_edits(self):
        baseline = self.configuration.load()
        for mode in ('source', 'private', 'authority', 'state', 'log'):
            with self.subTest(mode=mode):
                self.configuration.update(lambda value: value.update(baseline))
                self.fixture.fixture.identity.write_text('# Synthetic principal\nFixtureSurname FixtureGivenname\n')
                before = self.previous()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['ok'])
                if mode == 'state':
                    self.assertIn(b'2026-10-04T12:00:00.000Z', self.fixture.state.read_bytes())
                else:
                    self.assertEqual(self.fixture.state.read_bytes(), before[0])
                if mode == 'log':
                    self.assertIn(b'2026-10-04T12:00:00.000Z', self.fixture.log.read_bytes())
                else:
                    self.assertEqual(self.fixture.log.read_bytes(), before[1])
                self.assertFalse((self.fixture.root / 'LIFEOS/MEMORY/STATE/memory-operation.json').exists())

    def test_interruption_restores_previous_state_and_log(self):
        before = self.previous()
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.assertNotEqual(self.fixture.state.read_bytes(), before[0])
        self.assertEqual(self.fixture.log.read_bytes(), before[1])
        self.fixture.successful('--dry-run')
        self.assertEqual((self.fixture.state.read_bytes(), self.fixture.log.read_bytes()), before)

    def test_interruption_removes_new_state_destination(self):
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.assertTrue(self.fixture.state.exists())
        self.fixture.successful('--dry-run')
        self.assertFalse(self.fixture.state.exists())
        self.assertFalse(self.fixture.log.exists())

    def test_plan_recheck_refuses_changed_source_or_revoked_authority(self):
        service = MemoryService(self.configuration)
        context = self.fixture.fixture.fixture.context
        plan = service.native(context, 'derived_sync_plan', {'args': ['--force']})
        self.assertTrue(plan['ok'])
        self.fixture.fixture.identity.write_text('Synthetic later identity edit\n')
        result = service.native(context, 'derived_sync_check', {'args': ['--force'], 'signature': plan['signature']})
        self.assertFalse(result['ok'])
        plan = service.native(context, 'derived_sync_plan', {'args': ['--force']})
        self.assertTrue(plan['ok'])
        self.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        self.assertFalse(service.native(context, 'derived_sync_check',
            {'args': ['--force'], 'signature': plan['signature']})['ok'])
        self.assertFalse(self.fixture.state.exists())

    def test_malformed_argument_types_return_a_service_refusal(self):
        service = MemoryService(self.configuration)
        context = self.fixture.fixture.fixture.context
        for value in ({}, [None], [{}]):
            with self.subTest(value=value):
                result = service.native(context, 'derived_sync_plan', {'args': value})
                self.assertFalse(result['ok'])

    def test_failed_exit_cannot_be_reported_as_a_successful_child(self):
        from lifeos_hook_bridge.memory_derived_sync import _command
        service = MemoryService(self.configuration)
        context = self.fixture.fixture.fixture.context
        plan = service.native(context, 'derived_sync_plan', {'args': ['--force']})
        self.assertTrue(plan['ok'])
        self.fixture.fixture.successful()
        result = service.native(context, 'derived_sync_publish', {'args': ['--force'],
            'signature': plan['signature'], 'logs': [{
                'cmd': _command(plan['actions'][0]['cmd']), 'exit': 13, 'ms': 1}], 'failed': [False]})
        self.assertFalse(result['ok'])
        self.assertFalse(self.fixture.state.exists())
        self.assertFalse(self.fixture.log.exists())
