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

    def test_actual_host_worker_admission_reaches_model_guard_and_provider_tools(self):
        from unittest.mock import patch
        from hermes_cli.plugins import PluginContext, PluginManifest, get_plugin_manager
        from hermes_cli.middleware import run_llm_execution_middleware
        from gateway.session_context import set_session_vars, clear_session_vars
        with patch.dict(os.environ, {'HOME':str(self.fixture.fixture.home),'HERMES_HOME':str(self.fixture.home)}):
            tokens = set_session_vars(platform='chat-a',user_id='100',chat_id='200',chat_type='dm',session_id='session')
            manager = get_plugin_manager(); manager.discover_and_load()
            ctx = PluginContext(PluginManifest(name='memory-integration',version='1.0.0',description='Test'), manager)
            ctx.register_hook('pre_prompt_admission',lambda **kw:self.fixture.runtime.admit(self.fixture.metadata(), **self.fixture.route,is_first_turn=True))
            ctx.register_middleware('llm_admission',self.fixture.runtime.check_call,required=True)
            try:
                manager.invoke_hook('pre_prompt_admission',session_id='session')
                self.assertIsNone(self.fixture.runtime.context())
                dispatched = []
                run_llm_execution_middleware({'model':'synthetic-model'}, lambda req:dispatched.append(req), **self.fixture.route, session_id='session')
                self.assertEqual(len(dispatched),1)
                self.assertEqual(json.loads(self.provider.handle_tool_call('lifeos_memory_status',{}))['status'],'ok')
            finally:
                manager.unload(); clear_session_vars(tokens)

    def test_terminal_worker_uses_actual_host_platform_without_gateway_metadata(self):
        from unittest.mock import patch
        from hermes_cli.plugins import PluginContext, PluginManifest, get_plugin_manager
        from hermes_cli.middleware import run_llm_execution_middleware
        from gateway.session_context import set_session_vars, clear_session_vars
        from lifeos_hook_bridge.memory_context import current_host_metadata
        from lifeos_hook_bridge.memory_service import MemoryConfiguration
        self.fixture.configuration['accounts'][f'terminal:{os.getuid()}'] = 'owner'
        self.fixture.configuration['destinations'][f'terminal:{self.fixture.home}'] = dict(self.fixture.configuration['destinations']['chat-a:200'])
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        with patch.dict(os.environ, {'HOME':str(self.fixture.fixture.home),'HERMES_HOME':str(self.fixture.home)}):
            tokens = set_session_vars(platform='',session_id='terminal')
            manager = get_plugin_manager(); manager.discover_and_load()
            ctx = PluginContext(PluginManifest(name='memory-terminal',version='1.0.0',description='Test'), manager)
            ctx.register_hook('pre_prompt_admission',lambda **kw:self.fixture.runtime.admit(current_host_metadata(),**kw))
            ctx.register_middleware('llm_admission',self.fixture.runtime.check_call,required=True)
            try:
                manager.invoke_hook('pre_prompt_admission',session_id='terminal',platform='cli',is_first_turn=True,**self.fixture.route)
                self.assertIsNone(self.fixture.runtime.context())
                dispatched = []
                run_llm_execution_middleware({'model':'synthetic-model'},lambda req:dispatched.append(req),
                                             session_id='terminal',platform='cli',**self.fixture.route)
                self.assertEqual(len(dispatched),1)
                self.assertEqual(json.loads(self.provider.handle_tool_call('lifeos_memory_status',{}))['status'],'ok')
            finally:
                manager.unload(); clear_session_vars(tokens)

    def test_installed_bridge_loads_without_memory_selection_and_provider_namespace_shares_context(self):
        import io, logging, shutil
        from unittest.mock import patch
        from hermes_cli.plugins import get_plugin_manager
        from hermes_cli.middleware import run_llm_execution_middleware
        from plugins.memory import load_memory_provider
        from gateway.session_context import set_session_vars, clear_session_vars
        plugin = self.fixture.home / 'plugins/lifeos-hook-bridge'
        shutil.copytree(Path(__file__).parents[1] / 'lifeos_hook_bridge', plugin, ignore=shutil.ignore_patterns('__pycache__'))
        config = self.fixture.home / 'config.yaml'
        config.write_text('plugins:\n  enabled: [lifeos-hook-bridge]\nmemory:\n  provider: null\n')
        output = io.StringIO(); logger = logging.getLogger('hermes_cli.plugins')
        handler = logging.StreamHandler(output); handler.setLevel(logging.WARNING); logger.addHandler(handler)
        try:
            with patch.dict(os.environ, {'HOME':str(self.fixture.fixture.home),'HERMES_HOME':str(self.fixture.home),'LIFEOS_HOOK_SETTINGS':str(self.fixture.fixture.root / 'settings.json')}):
                manager = get_plugin_manager(); manager.discover_and_load()
                loaded = manager._plugins['lifeos-hook-bridge']
                self.assertEqual(loaded.manifest.kind,'standalone')
                self.assertTrue(loaded.enabled,loaded.error)
                self.assertTrue(manager.has_hook('pre_prompt_admission'))
                config.write_text('plugins:\n  enabled: [lifeos-hook-bridge]\nmemory:\n  provider: lifeos-hook-bridge\n')
                provider = load_memory_provider('lifeos-hook-bridge')
                self.assertIsNotNone(provider)
                self.assertNotEqual(provider.__class__.__module__,loaded.module.__name__+'.memory_provider')
                tokens = set_session_vars(platform='chat-a',user_id='100',chat_id='200',chat_type='dm',session_id='session')
                try:
                    manager.invoke_hook('pre_prompt_admission',user_message='synthetic',session_id='session',is_first_turn=True,**self.fixture.route)
                    dispatched = []
                    run_llm_execution_middleware({'model':'synthetic-model'},lambda req:dispatched.append(req),session_id='session',**self.fixture.route)
                    self.assertEqual(len(dispatched),1)
                    self.assertEqual(json.loads(provider.handle_tool_call('lifeos_memory_status',{}))['status'],'ok')
                finally:
                    clear_session_vars(tokens); provider.shutdown(); manager.unload()
        finally:
            logger.removeHandler(handler)
        for line in output.getvalue().splitlines():
            self.assertIn('declares Python dependencies',line)
