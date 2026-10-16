# ABOUTME: Review reproduction for PR34 mirror policy on an admitted Discord direct-message session.
# ABOUTME: Uses the actual runtime admission, native session store, and native mirror.
import os
import unittest
from unittest.mock import patch

from hermes_cli.plugins import PluginContext, PluginManifest, get_plugin_manager
from gateway.config import GatewayConfig
from gateway.mirror import mirror_to_session
from gateway.session import SessionStore

from lifeos_hook_bridge.discord_delivery import PrivateDiscordDelivery
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_runtime as runtime_fixture


class AdmittedDirectMessageMirrorReview(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        config = self.fixture.configuration
        config['accounts']['discord:20'] = 'owner'
        config['destinations']['discord:70'] = dict(config['destinations']['chat-a:200'])
        MemoryConfiguration(self.fixture.path).save(config)
        environment = patch.dict(os.environ, {'HERMES_HOME': str(self.fixture.home),
            'HOME': str(self.fixture.fixture.home)})
        environment.start(); self.addCleanup(environment.stop)
        self.manager = get_plugin_manager(); self.manager.discover_and_load()
        self.addCleanup(self.manager.unload)
        ctx = PluginContext(PluginManifest(name='notification-policy', version='1.0.0',
            description='Synthetic notification policy'), self.manager)
        ctx.register_hook('pre_message_delivery', PrivateDiscordDelivery(self.fixture.path).check)
        self.store = SessionStore(self.fixture.home / 'sessions', GatewayConfig())
        self.addCleanup(self.store.close_all_db_handles)
        self.store._db.create_session('dm-session', 'discord', chat_id='70', user_id='20', chat_type='dm')

    def test_admitted_direct_message_keeps_mirror(self):
        self.fixture.runtime.admit(self.fixture.metadata(app='discord', user='20', destination='70',
            session='dm-session'), **self.fixture.route, is_first_turn=True)
        print('admitted context', self.fixture.runtime.context())
        mirrored = mirror_to_session('discord', '70', 'Synthetic reply', source_label='cli',
            user_id='20', session_id='dm-session')
        print('admitted dm mirror', mirrored, len(self.store.load_transcript('dm-session')))
        self.assertTrue(mirrored)


if __name__ == '__main__':
    unittest.main()
