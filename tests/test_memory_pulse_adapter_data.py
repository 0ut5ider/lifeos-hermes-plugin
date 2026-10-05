# ABOUTME: Checks actual native PULSE cache readback and page pair publication.
# ABOUTME: Exercises caller policy, current source hashes, private text, and fixed destinations.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_pulse_adapter as adapter_fixture


class MemoryPulseAdapterDataTests(unittest.TestCase):
    def setUp(self):
        self.fixture = adapter_fixture.MemoryPulseAdapterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.cached()

    def call(self, action, *, value=None, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.fixture.home),
            PATH=str(self.fixture.bin), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.fixture.context))
        result = subprocess.run(['bun', '--no-install', str(Path(__file__).with_name('native_pulse_adapter_data.ts')),
            str(self.fixture.root)], input=json.dumps({'action': action, 'id': 'synthetic', 'value': value}),
            env=environment, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def page(self):
        return self.fixture.data / 'synthetic.json'

    def test_owner_reads_actual_native_page_and_metadata(self):
        result = self.call('read_page')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['value'], json.loads(self.page().read_text()))
        result = self.call('read_meta')
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['value'], json.loads((self.fixture.data / 'synthetic.meta.json').read_text()))

    def test_missing_context_refuses_cache_readback(self):
        self.assertFalse(self.call('read_page', context=False)['ok'])
        self.assertFalse(self.call('read_meta', context=False)['ok'])

    def test_restricted_reader_refuses_unclassified_cache(self):
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(read=['project'], projects=['lab']))
        self.assertFalse(self.call('read_page')['ok'])

    def test_changed_or_private_sources_exclude_cached_page_and_metadata(self):
        for content in ('# Synthetic collection\nA later synthetic book.\n',
                        '<private>Synthetic hidden collection.</private>\n'):
            with self.subTest(content=content):
                self.fixture.source.write_text(content)
                for action in ('read_page', 'read_meta'):
                    result = self.call(action)
                    self.assertTrue(result['ok'], result)
                    self.assertIsNone(result['value'])

    def test_escaped_private_page_text_is_excluded(self):
        value = json.loads(self.page().read_text())
        value['data']['items'][0]['name'] = '<private>Synthetic hidden page.</private>'
        self.page().write_text(json.dumps(value).replace('<', '\\u003c').replace('>', '\\u003e'))
        result = self.call('read_page')
        self.assertTrue(result['ok'], result)
        self.assertIsNone(result['value'])

    def test_owner_page_pair_publication_retains_native_data_and_private_permissions(self):
        value = json.loads(self.page().read_text())
        value['data']['title'] = 'Synthetic current page'
        result = self.call('write_page', value=value)
        self.assertTrue(result['ok'], result)
        self.assertEqual(json.loads(self.page().read_text()), value)
        meta = self.fixture.data / 'synthetic.meta.json'
        self.assertEqual(json.loads(meta.read_text()), value['_meta'])
        self.assertEqual(self.page().stat().st_mode & 0o777, 0o600)
        self.assertEqual(meta.stat().st_mode & 0o777, 0o600)

    def test_read_only_owner_page_write_preserves_previous_pair(self):
        before = self.page().read_bytes(), (self.fixture.data / 'synthetic.meta.json').read_bytes()
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        value = json.loads(before[0]); value['data']['title'] = 'Synthetic prohibited page'
        self.assertFalse(self.call('write_page', value=value)['ok'])
        self.assertEqual((self.page().read_bytes(), (self.fixture.data / 'synthetic.meta.json').read_bytes()), before)

    def test_changed_source_refuses_page_publication(self):
        before = self.page().read_bytes(), (self.fixture.data / 'synthetic.meta.json').read_bytes()
        value = json.loads(before[0]); value['data']['title'] = 'Synthetic stale page'
        self.fixture.source.write_text('Synthetic later source.\n')
        self.assertFalse(self.call('write_page', value=value)['ok'])
        self.assertEqual((self.page().read_bytes(), (self.fixture.data / 'synthetic.meta.json').read_bytes()), before)
