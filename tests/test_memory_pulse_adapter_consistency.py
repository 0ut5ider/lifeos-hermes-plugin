# ABOUTME: Verifies actual PULSE page conflicts and interrupted publication recovery.
# ABOUTME: Checks adapter input signatures against current source, prompt, and authority changes.
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_pulse_adapter_data as data_fixture
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryPulseAdapterConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = data_fixture.MemoryPulseAdapterDataTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.adapter = self.fixture.fixture
        self.configuration = self.adapter.fixture.configuration

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_pulse_adapter_process.py')),
            str(self.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def before(self):
        return (self.adapter.data / 'synthetic.json').read_bytes(), (self.adapter.data / 'synthetic.meta.json').read_bytes()

    def test_actual_post_validation_changes_refuse_page_publication(self):
        baseline = self.configuration.load()
        for mode in ('source', 'private', 'authority'):
            with self.subTest(mode=mode):
                self.configuration.update(lambda value: value.update(baseline))
                self.adapter.source.write_text('# Synthetic collection\nA synthetic book.\n')
                before = self.before()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertEqual(self.before(), before)

    def test_actual_interruption_restores_previous_page_and_metadata(self):
        before = self.before()
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.assertNotEqual((self.adapter.data / 'synthetic.json').read_bytes(), before[0])
        self.assertEqual((self.adapter.data / 'synthetic.meta.json').read_bytes(), before[1])
        result = self.fixture.call('read_page')
        self.assertTrue(result['ok'], result)
        self.assertEqual(self.before(), before)

    def manifest(self):
        return {'id': 'synthetic', 'title': 'Synthetic fixture', 'dataType': 'CollectionPageSchema',
            'sourceGlobs': ['LIFEOS/USER/TELOS/BOOKS.md'],
            'adapterPromptFile': 'LIFEOS/PULSE/pages/synthetic.adapter.md', 'model': 'haiku',
            'rebuildButton': True, 'order': 1, 'adapterVersion': '1.0.0'}

    def test_adapter_input_check_refuses_later_source_and_prompt_changes(self):
        service = MemoryService(self.configuration)
        context = self.adapter.fixture.context
        arguments = {'manifest': self.manifest(), 'force': False}
        plan = service.native(context, 'pulse_adapter_inputs', arguments)
        self.assertTrue(plan['ok'], plan)
        self.adapter.source.write_text('Synthetic later source edit.\n')
        self.assertFalse(service.native(context, 'pulse_adapter_check', {**arguments, 'signature': plan['signature']})['ok'])
        plan = service.native(context, 'pulse_adapter_inputs', arguments)
        self.assertTrue(plan['ok'], plan)
        prompt = self.adapter.root / arguments['manifest']['adapterPromptFile']
        prompt.write_text('Synthetic later prompt edit.\n')
        self.assertFalse(service.native(context, 'pulse_adapter_check', {**arguments, 'signature': plan['signature']})['ok'])

    def test_adapter_input_check_refuses_revoked_authority(self):
        service = MemoryService(self.configuration)
        context = self.adapter.fixture.context
        arguments = {'manifest': self.manifest(), 'force': False}
        plan = service.native(context, 'pulse_adapter_inputs', arguments)
        self.assertTrue(plan['ok'], plan)
        self.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        self.assertFalse(service.native(context, 'pulse_adapter_check', {**arguments, 'signature': plan['signature']})['ok'])
