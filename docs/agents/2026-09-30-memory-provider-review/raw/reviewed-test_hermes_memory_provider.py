# ABOUTME: Exercises the provider against the actual supported Hermes API and native files.
# ABOUTME: Verifies explicit tools, profile isolation, and absence of a second automatic extractor.
import json
import os
from pathlib import Path
import sys
import unittest

HOST = Path(os.environ.get('LIFEOS_HERMES_SOURCE', str(Path.home() / '.cache/lifeos-plugin-memory/source-gate-20260930-native/hermes')))
sys.path.insert(0,str(HOST))
from lifeos_hook_bridge.memory_provider import LifeOSMemoryProvider
import test_memory_runtime as runtime_fixture

class HermesMemoryProviderTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.provider = LifeOSMemoryProvider(self.fixture.path)
    def test_explicit_tools_use_the_native_store_and_current_author(self):
        self.assertTrue(self.provider.is_available())
        self.provider.initialize('session', hermes_home=str(self.fixture.home))
        self.fixture.admit()
        saved = json.loads(self.provider.handle_tool_call('lifeos_memory_remember', {
            'category':'project','content':'Synthetic provider marker','title':'Synthetic provider',
            'project':'lab','request_id':'provider-save'},session_id='session'))
        self.assertEqual(saved['status'],'committed',saved)
        self.assertEqual(saved['writer'],'chat-a:100')
        result = self.fixture.fixture.memory.get(__import__('test_memory_native').OWNER, saved['reference'])
        self.assertEqual(result['content'],'Synthetic provider marker')
        denied = json.loads(self.provider.handle_tool_call('lifeos_memory_get', {'reference':saved['reference']},session_id='other'))
        self.assertEqual(denied['status'],'rejected')
    def test_provider_does_not_duplicate_native_automatic_recall_or_review(self):
        self.assertEqual(self.provider.prefetch('synthetic query'), '')
        self.assertIsNone(self.provider.sync_turn('user','assistant'))
        self.assertEqual(self.provider.on_pre_compress([]), '')
        self.assertEqual(len(self.provider.get_tool_schemas()),6)
    def test_profile_mismatch_and_session_switch_reject_stale_tools(self):
        with self.assertRaisesRegex(RuntimeError,'different Hermes profile'):
            self.provider.initialize('session',hermes_home=str(self.fixture.home / 'other'))
        self.fixture.admit()
        self.provider.on_session_switch('other')
        result = json.loads(self.provider.handle_tool_call('lifeos_memory_status',{}))
        self.assertEqual(result['status'],'rejected')
    def test_config_revocation_is_visible_without_provider_recreation(self):
        before = self.provider.identity_signature()
        self.fixture.configuration['ownership_enabled'] = False
        from lifeos_hook_bridge.memory_service import MemoryConfiguration
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.assertNotEqual(before, self.provider.identity_signature())
        self.assertFalse(self.provider.is_available())
