# ABOUTME: Review reproduction for PR34 mirror policy on destinations LifeOS does not govern.
# ABOUTME: Uses the PR34 test fixture with the actual native mirror and session store.
import os
import unittest

from gateway.mirror import mirror_to_session
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_discord_notification_mirror as base


class UnboundMirrorReview(base.DiscordNotificationMirrorTests):
    def mirror_to(self, chat_id, identifier):
        self.db.create_session(identifier, 'discord', chat_id=chat_id, user_id='20', chat_type='dm')
        return mirror_to_session('discord', chat_id, 'Synthetic reply', source_label='cli',
            user_id='20', session_id=identifier)

    def test_review_returned_ownership_unbound_destination(self):
        self.fixture.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        print('policy', self.policy.check(platform='discord', chat_id='999',
            hermes_home=str(self.fixture.home), purpose='mirror', session_id='dm-session'))
        mirrored = self.mirror_to('999', 'dm-session')
        print('returned-ownership unbound mirror', mirrored,
              len(self.store.load_transcript('dm-session')))
        self.assertTrue(mirrored)

    def test_review_missing_memory_configuration(self):
        os.unlink(self.fixture.path)
        print('policy', self.policy.check(platform='discord', chat_id='999',
            hermes_home=str(self.fixture.home), purpose='mirror', session_id='dm-session'))
        mirrored = self.mirror_to('999', 'dm-session')
        print('missing-configuration mirror', mirrored,
              len(self.store.load_transcript('dm-session')))
        self.assertTrue(mirrored)

    def test_review_returned_ownership_changed_audience(self):
        self.fixture.configuration['ownership_enabled'] = False
        MemoryConfiguration(self.fixture.path).save(self.fixture.configuration)
        self.audience.responses['/channels/60']['permission_overwrites'].append(
            {'id': '40', 'type': 1, 'allow': '1024', 'deny': '0'})
        mirrored = self.mirror()
        print('returned-ownership shared-audience mirror', mirrored)
        self.assertTrue(mirrored)


del base.DiscordNotificationMirrorTests
if __name__ == '__main__':
    unittest.main()
