# ABOUTME: Exercises actual Discord SDK sends and edits against a private HTTP fixture.
# ABOUTME: Changes channel access between generation, chunks, retries, and delivery.
import asyncio
import copy
import importlib.util
from pathlib import Path
import threading
from unittest.mock import patch
import unittest

import discord
from agent.secret_scope import set_secret_scope, reset_secret_scope
from hermes_constants import get_hermes_home
from hermes_cli.plugins import get_plugin_manager
from plugins.platforms.discord import adapter as adapter_module

from lifeos_hook_bridge.discord_audience import DiscordAPI, resolve_audience
from lifeos_hook_bridge.discord_delivery import PrivateDiscordDelivery
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_discord_audience as audience_fixture


class DiscordPrivateDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.audience = audience_fixture.DiscordAudienceTests()
        self.audience.setUp()
        self.addCleanup(self.audience.doCleanups)
        self.addAsyncCleanup(asyncio.to_thread, self.audience.server.shutdown)
        source = Path(adapter_module.__file__).resolve().parents[3] / 'tests/gateway/test_discord_guild_channel_only.py'
        spec = importlib.util.spec_from_file_location('private_channel_fixture', source)
        fixture_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture_module)
        self.gateway = fixture_module.GuildChannelOnlyTests()
        self.gateway.setUp()
        self.addCleanup(self.gateway.doCleanups)
        token = set_secret_scope({'DISCORD_BOT_TOKEN':'synthetic-token'})
        self.addCleanup(reset_secret_scope, token)
        self.adapter = self.gateway.adapter
        self.audience.responses['/users/@me'] = self.gateway.bot_data
        self.route_base = patch.object(discord.http.Route, 'BASE', self.audience.origin)
        self.route_base.start()
        self.addCleanup(self.route_base.stop)
        api_base = patch.object(adapter_module,'_DISCORD_API_BASE',self.audience.origin)
        api_base.start()
        self.addCleanup(api_base.stop)
        await self.gateway.client._async_setup_hook()
        await self.gateway.client.http.static_login('synthetic-token')
        self.addAsyncCleanup(self.gateway.client.close)
        configuration = copy.deepcopy(self.audience.configuration)
        configuration.update(root=str(get_hermes_home() / 'synthetic-lifeos'),
            ownership_enabled=False, sharing_enabled=False, clients={})
        self.configuration = MemoryConfiguration(get_hermes_home() / 'lifeos-memory.json')
        self.configuration.save(configuration)
        self.api = DiscordAPI('synthetic-token', origin=self.audience.origin)
        self.policy = PrivateDiscordDelivery(self.configuration.path,
            audience_lookup=lambda configuration, metadata: resolve_audience(configuration,metadata,api=self.api))
        self.manager = get_plugin_manager()
        self.calls = []
        self.manager._hooks['pre_message_delivery'] = [self.guard]

    def guard(self, platform='', chat_id='', guild_id='', hermes_home='', **_):
        self.calls.append((platform,chat_id,guild_id,hermes_home))
        return self.policy.check(platform=platform,chat_id=chat_id,guild_id=guild_id,hermes_home=hermes_home)

    def open_channel(self):
        self.audience.responses['/channels/60']['permission_overwrites'].append(
            {'id':'40','type':1,'allow':'1024','deny':'0'})

    async def refused(self, operation):
        with self.assertLogs(adapter_module.logger, level='WARNING') as logged:
            result = await operation
        self.assertTrue(any('private delivery' in row.lower() for row in logged.output), logged.output)
        return result

    async def test_private_audience_permits_an_actual_sdk_post(self):
        result = await self.adapter.send('60','Synthetic private reply')
        self.assertTrue(result.success, result)
        self.assertEqual(len(self.audience.deliveries),1)
        self.assertEqual(self.audience.deliveries[0]['payload']['content'],'Synthetic private reply')
        self.assertEqual(self.calls[-1],('discord','60','10',str(get_hermes_home())))

    async def test_changed_audience_withholds_generated_reply(self):
        self.open_channel()
        result = await self.refused(self.adapter.send('60','Synthetic withheld reply'))
        self.assertFalse(result.success, result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_overflow_edit_stops_after_the_audience_changes(self):
        self.audience.on_delivery = self.open_channel
        result = await self.refused(self.adapter.edit_message('60','100000000000000000',
            'Synthetic first chunk\n'+('a'*1900)+'\n'+('b'*1900),finalize=True))
        self.assertFalse(result.success,result)
        self.assertEqual(len(self.audience.deliveries),1)
        self.assertEqual(self.audience.deliveries[0]['method'],'PATCH')

    async def test_prompt_delivery_rechecks_the_current_audience(self):
        self.open_channel()
        result = await self.refused(self.adapter._send_prompt('60',None,
            lambda channel: ({'content':'Synthetic private question'},None),fail_log='Synthetic test prompt'))
        self.assertFalse(result.success,result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_changed_configuration_during_permission_reads_withholds_delivery(self):
        def change_binding(path):
            if path == '/guilds/10/members?limit=1000':
                self.configuration.update(lambda value: value['discord_channels'].clear())
                self.audience.on_request = None
        self.audience.on_request = change_binding
        result = await self.refused(self.adapter.send('60','Synthetic changed binding'))
        self.assertFalse(result.success,result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_another_profile_withholds_the_reply(self):
        self.manager._hooks['pre_message_delivery'] = [lambda **kwargs: self.policy.check(
            **{**kwargs,'hermes_home':str(get_hermes_home() / 'different-profile')})]
        result = await self.refused(self.adapter.send('60','Synthetic wrong profile'))
        self.assertFalse(result.success,result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_another_transport_token_withholds_the_reply(self):
        self.gateway.client.http.token = 'other-synthetic-token'
        with self.assertLogs(adapter_module.logger,level='ERROR') as logged:
            result = await self.adapter.send('60','Synthetic wrong token')
        self.assertFalse(result.success,result)
        self.assertIn('different profile credential',logged.output[0])
        self.assertEqual(self.audience.deliveries,[])
        self.assertEqual(self.calls,[])

    async def test_each_chunk_rechecks_the_current_audience(self):
        self.audience.on_delivery = self.open_channel
        result = await self.refused(self.adapter.send('60','Synthetic first chunk\n'+('a'*1900)+'\nSynthetic second chunk\n'+('b'*1900)))
        self.assertFalse(result.success, result)
        self.assertEqual(len(self.audience.deliveries),1)
        self.assertNotIn('b'*100,self.audience.deliveries[0]['payload']['content'])
        self.assertEqual(len(self.calls),2)

    async def test_streaming_edit_rechecks_the_current_audience(self):
        self.open_channel()
        result = await self.refused(self.adapter.edit_message('60','100000000000000000','Synthetic private update'))
        self.assertFalse(result.success, result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_missing_required_guard_withholds_the_reply(self):
        self.manager._hooks['pre_message_delivery'] = []
        result = await self.refused(self.adapter.send('60','Synthetic unguarded reply'))
        self.assertFalse(result.success, result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_unknown_guard_result_withholds_the_reply(self):
        self.manager._hooks['pre_message_delivery'] = [lambda **_: {'status':'ok'}]
        result = await self.refused(self.adapter.send('60','Synthetic unknown admission'))
        self.assertFalse(result.success, result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_optional_channel_mode_preserves_actual_delivery(self):
        self.adapter.config.extra = {}
        self.manager._hooks['pre_message_delivery'] = []
        result = await self.adapter.send('60','Synthetic ordinary reply')
        self.assertTrue(result.success, result)
        self.assertEqual(len(self.audience.deliveries),1)

    async def test_standalone_delivery_rechecks_the_current_audience(self):
        from gateway.config import PlatformConfig
        self.open_channel()
        result = await self.refused(adapter_module._standalone_send(PlatformConfig(token='synthetic-token',
            extra={'guild_channel_only':True,'allowed_channels':['60']}),'60','Synthetic standalone reply'))
        self.assertFalse(result.get('success'),result)
        self.assertEqual(self.audience.deliveries,[])

    async def test_private_audience_allows_actual_standalone_delivery(self):
        from gateway.config import PlatformConfig
        result = await adapter_module._standalone_send(PlatformConfig(token='synthetic-token',
            extra={'guild_channel_only':True,'allowed_channels':['60']}),'60','Synthetic standalone reply')
        self.assertTrue(result.get('success'),result)
        self.assertEqual(len(self.audience.deliveries),1)
        self.assertEqual(len(self.calls),2)

    async def test_a_changed_audience_withholds_an_actual_file_upload(self):
        path = get_hermes_home() / 'synthetic.txt'
        path.write_text('Synthetic private attachment\n')
        self.open_channel()
        result = await self.refused(self.adapter.send_document('60',str(path),caption='Synthetic private caption'))
        self.assertFalse(result.success,result)
        self.assertEqual(self.audience.deliveries,[])

    async def question_view(self):
        result = await self.adapter.send_clarify('60','Synthetic private question',
            ['Synthetic-A','Synthetic-B'],'synthetic-clarify','synthetic-session')
        self.assertTrue(result.success,result)
        view = self.gateway.client._connection._view_store._synced_message_views[int(result.message_id)]
        self.addCleanup(view.stop)
        return view

    async def test_expired_question_withholds_its_card_after_an_audience_change(self):
        view = await self.question_view()
        self.open_channel()
        await view.on_timeout()
        self.assertEqual(len(self.audience.deliveries),1)

    async def test_expired_question_updates_its_card_with_an_unchanged_audience(self):
        view = await self.question_view()
        await view.on_timeout()
        self.assertEqual(len(self.audience.deliveries),2)
        self.assertEqual(self.audience.deliveries[-1]['method'],'PATCH')

    async def test_expired_choice_picker_withholds_its_card_after_an_audience_change(self):
        async def selected(*_):
            raise AssertionError('Expiry must not select an option')
        result = await self.adapter.send_choice_picker('60','Synthetic private picker',
            [{'value':'synthetic','label':'Synthetic private choice','is_current':False}],
            'synthetic-session',selected)
        self.assertTrue(result.success,result)
        view = self.gateway.client._connection._view_store._synced_message_views[int(result.message_id)]
        self.addCleanup(view.stop)
        self.open_channel()
        await view.on_timeout()
        self.assertEqual(len(self.audience.deliveries),1)

    async def test_standalone_attachment_stops_after_the_audience_changes(self):
        from gateway.config import PlatformConfig
        path = get_hermes_home() / 'synthetic.txt'
        path.write_text('Synthetic private attachment\n')
        self.audience.on_delivery = self.open_channel
        result = await self.refused(adapter_module._standalone_send(PlatformConfig(token='synthetic-token',
            extra={'guild_channel_only':True,'allowed_channels':['60']}),'60','Synthetic standalone text',
            media_files=[(str(path),False)]))
        self.assertFalse(result.get('success'),result)
        self.assertEqual(len(self.audience.deliveries),1)

    async def test_policy_exception_withholds_delivery(self):
        def failed(**_):
            raise RuntimeError('Synthetic delivery policy failure')
        self.manager._hooks['pre_message_delivery'] = [failed]
        with self.assertLogs(level='WARNING') as logged:
            result = await self.adapter.send('60','Synthetic policy failure')
        self.assertFalse(result.success,result)
        self.assertTrue(any('Synthetic delivery policy failure' in row for row in logged.output))
        self.assertEqual(self.audience.deliveries,[])

    async def test_a_late_policy_grant_cannot_resume_delivery(self):
        completed = threading.Event()
        def late(**_):
            completed.wait(0.15)
            completed.set()
            return {'action':'allow'}
        self.manager._hooks['pre_message_delivery'] = [late]
        with patch('hermes_cli.plugins._resolve_hook_callback_timeout',return_value=0.02):
            with self.assertLogs(level='WARNING') as logged:
                result = await self.adapter.send('60','Synthetic late policy grant')
        self.assertFalse(result.success,result)
        self.assertTrue(any('timed out' in row for row in logged.output))
        await asyncio.to_thread(completed.wait,1)
        self.assertEqual(self.audience.deliveries,[])


if __name__ == '__main__':
    unittest.main()
