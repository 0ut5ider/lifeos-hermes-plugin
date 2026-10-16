# ABOUTME: Exercises delivery mirroring with actual private-audience and native session fixtures.
# ABOUTME: Keeps notifications from creating unverified history before the first admitted turn.
import asyncio
import json
import os
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from hermes_cli.plugins import PluginContext, PluginManifest, get_plugin_manager
from gateway.config import GatewayConfig
from gateway.mirror import mirror_to_session
from gateway.session import SessionStore
from agent.turn_context import _collect_pre_llm_call_context

from lifeos_hook_bridge.discord_audience import DiscordAPI, resolve_audience
from lifeos_hook_bridge.discord_delivery import PrivateDiscordDelivery
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_discord_audience as audience_fixture
import test_memory_runtime as runtime_fixture


class DiscordNotificationMirrorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.audience = audience_fixture.DiscordAudienceTests()
        self.audience.setUp()
        self.addCleanup(self.audience.doCleanups)
        config = self.fixture.configuration
        grant = dict(config['destinations']['chat-a:200'])
        config['accounts'] = dict(self.audience.configuration['accounts'])
        config['destinations'] = {'discord:60': grant}
        config['discord_channels'] = self.audience.configuration['discord_channels']
        MemoryConfiguration(self.fixture.path).save(config)
        api = DiscordAPI('synthetic-token', origin=self.audience.origin)
        lookup = lambda configuration, metadata: resolve_audience(configuration, metadata, api=api)
        self.fixture.runtime.audience_lookup = lookup
        self.policy = PrivateDiscordDelivery(self.fixture.path, audience_lookup=lookup)
        environment = patch.dict(os.environ, {'HERMES_HOME': str(self.fixture.home),
            'HOME': str(self.fixture.fixture.home)})
        environment.start()
        self.addCleanup(environment.stop)
        self.manager = get_plugin_manager()
        self.manager.discover_and_load()
        self.addCleanup(self.manager.unload)
        ctx = PluginContext(PluginManifest(name='notification-policy', version='1.0.0',
            description='Synthetic notification policy'), self.manager)
        ctx.register_hook('pre_message_delivery', self.policy.check)
        ctx.register_hook('pre_prompt_admission', self.admit_hook)
        self.store = SessionStore(self.fixture.home / 'sessions', GatewayConfig())
        self.addCleanup(self.store.close_all_db_handles)
        self.db = self.store._db
        self.new_session('notification-session')
        self.admissions = []

    def new_session(self, identifier):
        self.db.create_session(identifier, 'discord', chat_id='60', user_id='20', chat_type='group')

    def metadata(self, identifier):
        return {**self.audience.metadata, 'HERMES_SESSION_ID': identifier}

    def admit_hook(self, **kwargs):
        self.admissions.append(kwargs['is_first_turn'])
        self.fixture.runtime.admit(self.metadata(kwargs['session_id']), **kwargs)

    def mirror(self, identifier='notification-session'):
        return mirror_to_session('discord', '60', 'Synthetic morning notice',
            source_label='cli', user_id='20', session_id=identifier)

    def test_notice_before_first_human_turn_preserves_empty_history_and_admission(self):
        self.assertFalse(self.mirror())
        history = self.store.load_transcript('notification-session')
        self.assertEqual(history, [])
        agent = SimpleNamespace(session_id='notification-session', platform='discord',
            **self.fixture.route)
        _collect_pre_llm_call_context(agent, effective_task_id='synthetic', turn_id='synthetic',
            original_user_message='Synthetic hello',
            messages=[{'role': 'user', 'content': 'Synthetic hello'}], conversation_history=history)
        self.assertEqual(self.admissions, [True])

    def test_admitted_conversation_keeps_the_native_delivery_mirror(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        self.assertTrue(self.mirror())
        history = self.store.load_transcript('notification-session')
        self.assertEqual([(row['role'], row['content']) for row in history],
            [('assistant', 'Synthetic morning notice')])

    def test_notification_does_not_create_an_admission(self):
        self.assertFalse(self.mirror())
        self.assertFalse(self.fixture.runtime.state_path.exists())

    def test_another_native_session_cannot_borrow_an_admission(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        self.new_session('another-session')
        self.assertFalse(self.mirror('another-session'))
        self.assertEqual(self.store.load_transcript('another-session'), [])

    def test_another_author_cannot_supply_the_destination_admission(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        states = self.fixture.runtime._states()
        states['notification-session']['context']['author'] = '40'
        self.fixture.runtime.state_path.write_text(json.dumps(states))
        self.assertFalse(self.mirror())
        self.assertEqual(self.store.load_transcript('notification-session'), [])

    def test_returned_memory_ownership_preserves_standard_mirroring(self):
        self.fixture.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.assertTrue(self.mirror())
        self.assertEqual(len(self.store.load_transcript('notification-session')), 1)

    def test_revoked_scope_does_not_keep_mirroring(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        self.fixture.configuration['destinations']['discord:60']['write'] = []
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.assertFalse(self.mirror())
        self.assertEqual(self.store.load_transcript('notification-session'), [])

    def test_changed_audience_does_not_keep_mirroring(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        self.audience.responses['/channels/60']['permission_overwrites'].append(
            {'id': '40', 'type': 1, 'allow': '1024', 'deny': '0'})
        self.assertFalse(self.mirror())
        self.assertEqual(self.store.load_transcript('notification-session'), [])

    def test_private_delivery_still_succeeds_without_a_foreground_admission(self):
        result = self.policy.check(platform='discord', chat_id='60',
            hermes_home=str(self.fixture.home))
        self.assertEqual(result, {'action': 'allow'})

    def test_actual_standalone_notice_delivers_without_creating_unadmitted_history(self):
        from agent.secret_scope import set_secret_scope, reset_secret_scope
        from gateway.config import PlatformConfig
        from plugins.platforms.discord import adapter
        token = set_secret_scope({'DISCORD_BOT_TOKEN': 'synthetic-token'})
        self.addCleanup(reset_secret_scope, token)
        with patch.object(adapter, '_DISCORD_API_BASE', self.audience.origin):
            result = asyncio.run(adapter._standalone_send(PlatformConfig(token='synthetic-token',
                extra={'guild_channel_only': True, 'allowed_channels': ['60']}),
                '60', 'Synthetic morning notice'))
        self.assertTrue(result.get('success'), result)
        self.assertEqual(len(self.audience.deliveries), 1)
        self.assertFalse(self.mirror())
        self.assertEqual(self.store.load_transcript('notification-session'), [])

    def test_no_delivery_policy_preserves_standard_hermes_mirroring(self):
        self.manager._hooks['pre_message_delivery'] = []
        self.assertTrue(self.mirror())
        self.assertEqual(len(self.store.load_transcript('notification-session')), 1)

    def test_returned_ownership_keeps_unbound_destination_mirrors(self):
        self.fixture.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.db.create_session('unbound-session', 'discord', chat_id='999', user_id='20', chat_type='dm')
        self.assertTrue(mirror_to_session('discord', '999', 'Synthetic notice',
            session_id='unbound-session'))
        self.assertEqual(len(self.store.load_transcript('unbound-session')), 1)

    def test_absent_memory_configuration_keeps_hermes_mirrors(self):
        self.fixture.path.unlink()
        self.assertTrue(self.mirror())
        self.assertEqual(len(self.store.load_transcript('notification-session')), 1)

    def test_invalid_memory_configuration_still_refuses_mirrors(self):
        self.fixture.path.write_text('{')
        self.assertFalse(self.mirror())

    def test_returned_ownership_keeps_mirrors_when_channel_audience_changes(self):
        self.fixture.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.audience.responses['/channels/60']['permission_overwrites'].append(
            {'id': '40', 'type': 1, 'allow': '1024', 'deny': '0'})
        self.assertTrue(self.mirror())
        self.assertEqual(self.audience.requests, [])

    def test_admitted_direct_message_keeps_mirror_without_a_channel_binding(self):
        config = self.fixture.configuration
        del config['discord_channels']
        config['destinations']['discord:70'] = dict(config['destinations']['discord:60'])
        MemoryConfiguration(self.fixture.path).save(config)
        self.db.create_session('dm-session', 'discord', chat_id='70', user_id='20', chat_type='dm')
        self.fixture.runtime.admit(self.fixture.metadata(app='discord', user='20',
            destination='70', session='dm-session'), **self.fixture.route, is_first_turn=True)
        self.assertTrue(mirror_to_session('discord', '70', 'Synthetic notice', session_id='dm-session'))
        self.assertEqual(len(self.store.load_transcript('dm-session')), 1)
        self.assertEqual(self.audience.requests, [])

    def test_send_tool_resolves_real_gateway_session_before_and_after_admission(self):
        from tools.send_message_tool import _mirror_sent_message
        from gateway.config import Platform
        from gateway.session import SessionSource
        entry = self.store.get_or_create_session(SessionSource(platform=Platform.DISCORD,
            chat_id='60', chat_type='group', user_id='20', scope_id='10'))
        self.assertFalse(_mirror_sent_message('discord', '60', 'Synthetic morning notice', None))
        self.assertEqual(self.store.load_transcript(entry.session_id), [])
        self.fixture.runtime.admit(self.metadata(entry.session_id),
            **self.fixture.route, is_first_turn=True)
        self.assertTrue(_mirror_sent_message('discord', '60', 'Synthetic morning notice', None))
        self.assertEqual(len(self.store.load_transcript(entry.session_id)), 1)

    def test_webhook_mirror_checks_run_outside_the_gateway_event_loop(self):
        from agent.secret_scope import set_secret_scope, reset_secret_scope
        from gateway.config import Platform, PlatformConfig
        from gateway.platforms.base import SendResult
        from gateway.platforms.webhook import WebhookAdapter
        from gateway.session import SessionSource
        from plugins.platforms.discord import adapter
        entry = self.store.get_or_create_session(SessionSource(platform=Platform.DISCORD,
            chat_id='60', chat_type='group', user_id='20', scope_id='10'))
        self.fixture.runtime.admit(self.metadata(entry.session_id),
            **self.fixture.route, is_first_turn=True)
        callback_threads = []
        mirror_started = threading.Event()
        heartbeat_seen = threading.Event()
        heartbeat_unblocked_request = []
        self.audience.requests.clear()

        def await_heartbeat(path):
            if path == '/users/@me' and self.audience.deliveries:
                mirror_started.set()
                heartbeat_unblocked_request.append(heartbeat_seen.wait(timeout=1))

        self.audience.on_request = await_heartbeat

        def observe_thread(**kwargs):
            if kwargs.get('purpose') == 'mirror':
                callback_threads.append(threading.get_ident())
            return {'action': 'allow'}

        ctx = PluginContext(PluginManifest(name='mirror-thread-probe', version='1.0.0',
            description='Synthetic thread measurement'), self.manager)
        ctx.register_hook('pre_message_delivery', observe_thread)

        class LocalDiscordAdapter:
            async def send(self, chat_id, content, metadata=None):
                result = await adapter._standalone_send(PlatformConfig(token='synthetic-token',
                    extra={'guild_channel_only': True, 'allowed_channels': ['60']}), chat_id, content)
                return SendResult(success=result.get('success', False))

        webhook = WebhookAdapter(PlatformConfig())
        webhook.gateway_runner = SimpleNamespace(
            _authorization_adapter=lambda platform, profile: LocalDiscordAdapter())
        token = set_secret_scope({'DISCORD_BOT_TOKEN': 'synthetic-token'})
        self.addCleanup(reset_secret_scope, token)
        loop_thread = threading.get_ident()

        async def deliver_with_heartbeat():
            async def heartbeat():
                while not mirror_started.is_set():
                    await asyncio.sleep(0.001)
                heartbeat_seen.set()

            pulse = asyncio.create_task(heartbeat())
            try:
                return await webhook._deliver_cross_platform('discord', 'Synthetic webhook notice',
                    {'mirror': True, 'route': 'synthetic', 'deliver_extra': {'chat_id': '60'}})
            finally:
                await asyncio.wait_for(pulse, timeout=2)

        with patch.object(adapter, '_DISCORD_API_BASE', self.audience.origin):
            result = asyncio.run(deliver_with_heartbeat())
        self.assertTrue(result.success)
        self.assertEqual(len(self.audience.deliveries), 1)
        self.assertEqual(len(self.store.load_transcript(entry.session_id)), 1)
        self.assertEqual(len(callback_threads), 1)
        self.assertNotEqual(callback_threads[0], loop_thread)
        self.assertEqual(heartbeat_unblocked_request, [True])
