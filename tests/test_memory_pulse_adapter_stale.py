# ABOUTME: Verifies caller admission before native PULSE metadata-age readback.
# ABOUTME: Preserves actual owned-file age and native missing-file behavior.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_pulse_adapter as adapter_fixture


class MemoryPulseAdapterStaleTests(unittest.TestCase):
    def setUp(self):
        self.fixture = adapter_fixture.MemoryPulseAdapterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.cached()

    def call(self, *, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.fixture.home), PATH=str(self.fixture.bin))
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.fixture.context))
        result = subprocess.run(['bun', '--no-install', str(Path(__file__).with_name('native_pulse_adapter_stale.ts')),
            str(self.fixture.root)], env=environment, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_missing_context_cannot_read_cache_age(self):
        self.assertFalse(self.call(context=False)['ok'])

    def test_restricted_context_cannot_read_cache_age(self):
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(read=['project'], projects=['lab']))
        self.assertFalse(self.call()['ok'])

    def test_owner_retains_native_age_and_missing_file_results(self):
        result = self.call()
        self.assertTrue(result['ok'], result)
        self.assertFalse(result['value']['stale'])
        self.assertLess(result['value']['ageHours'], 1)
        (self.fixture.data / 'synthetic.meta.json').unlink()
        result = self.call()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['value'], {'stale': True, 'ageHours': None})
