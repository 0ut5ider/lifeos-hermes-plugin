# ABOUTME: Round 2 review probes for PR34 mirror admission against synthetic fixtures.
# ABOUTME: Checks revoked DM authority, unbound channels, and webhook event-loop behavior.
import asyncio
import json
import unittest
from unittest.mock import patch

from gateway.mirror import mirror_to_session
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_discord_notification_mirror as pr


class Round2Probes(pr.DiscordNotificationMirrorTests):
    def admit_dm(self):
        config = self.fixture.configuration
        del config['discord_channels']
        config['destinations']['discord:70'] = dict(config['destinations']['discord:60'])
        MemoryConfiguration(self.fixture.path).save(config)
        self.db.create_session('dm-session', 'discord', chat_id='70', user_id='20', chat_type='dm')
        self.fixture.runtime.admit(self.fixture.metadata(app='discord', user='20',
            destination='70', session='dm-session'), **self.fixture.route, is_first_turn=True)
        return config

    def dm_mirror(self, session='dm-session'):
        return mirror_to_session('discord', '70', 'Synthetic notice', session_id=session)

    def test_probe_dm_mirror_refused_after_owner_account_removed(self):
        config = self.admit_dm()
        del config['accounts']['discord:20']
        MemoryConfiguration(self.fixture.path).save(config)
        decision = self.policy.check(platform='discord', chat_id='70',
            hermes_home=str(self.fixture.home), purpose='mirror', session_id='dm-session')
        print('removed-account decision', decision)
        self.assertFalse(self.dm_mirror())
        self.assertEqual(self.store.load_transcript('dm-session'), [])

    def test_probe_dm_mirror_refused_after_grant_revoked(self):
        config = self.admit_dm()
        del config['destinations']['discord:70']
        MemoryConfiguration(self.fixture.path).save(config)
        decision = self.policy.check(platform='discord', chat_id='70',
            hermes_home=str(self.fixture.home), purpose='mirror', session_id='dm-session')
        print('revoked-grant decision', decision)
        self.assertFalse(self.dm_mirror())
        self.assertEqual(self.store.load_transcript('dm-session'), [])

    def test_probe_dm_mirror_refused_for_unadmitted_dm_session(self):
        self.admit_dm()
        self.db.create_session('dm-other', 'discord', chat_id='70', user_id='20', chat_type='dm')
        self.assertFalse(self.dm_mirror('dm-other'))
        self.assertEqual(self.store.load_transcript('dm-other'), [])

    def test_probe_dm_session_cannot_mirror_into_bound_channel_destination(self):
        self.admit_dm()
        config = self.fixture.configuration
        config['discord_channels'] = self.audience.configuration['discord_channels']
        MemoryConfiguration(self.fixture.path).save(config)
        decision = self.policy.check(platform='discord', chat_id='60',
            hermes_home=str(self.fixture.home), purpose='mirror', session_id='dm-session')
        print('dm-session into bound 60 decision', decision)
        self.assertNotEqual(decision.get('mirror'), True)

    def test_probe_dm_mirror_refused_when_state_file_permissions_unsafe(self):
        self.admit_dm()
        self.fixture.runtime.state_path.chmod(0o644)
        decision = self.policy.check(platform='discord', chat_id='70',
            hermes_home=str(self.fixture.home), purpose='mirror', session_id='dm-session')
        print('unsafe-state decision', decision)
        self.assertFalse(self.dm_mirror())

    def test_probe_dm_mirror_refused_for_other_profile_home(self):
        self.admit_dm()
        decision = self.policy.check(platform='discord', chat_id='70',
            hermes_home=str(self.fixture.home / 'other'), purpose='mirror', session_id='dm-session')
        print('other-home decision', decision)
        self.assertEqual(decision['action'], 'block')

    def test_probe_channel_unbound_after_admission(self):
        # Observation probe: a guild channel admitted while bound, then unbound, is
        # evaluated by the unbound path. Records the decision and the next admission.
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        before = self.fixture.runtime._states()['notification-session']['scope']
        config = self.fixture.configuration
        del config['discord_channels']
        MemoryConfiguration(self.fixture.path).save(config)
        self.audience.requests.clear()
        decision = self.policy.check(platform='discord', chat_id='60',
            hermes_home=str(self.fixture.home), purpose='mirror', session_id='notification-session')
        print('unbound-after-admission decision', decision, 'requests', self.audience.requests)
        mirrored = self.mirror()
        print('unbound-after-admission mirrored', mirrored,
              'history', len(self.store.load_transcript('notification-session')))
        try:
            self.fixture.runtime.admit(self.metadata('notification-session'), **self.fixture.route)
            print('next admission: admitted')
        except Exception as error:
            print('next admission refused:', type(error).__name__, error)
        print('scope unchanged', before == self.fixture.runtime._states()['notification-session']['scope'])

    def test_probe_webhook_synchronous_baseline_blocks_heartbeat(self):
        # Reproduces the pre-fix caller by running the mirror synchronously on the loop.
        from gateway.platforms import webhook as webhook_module

        async def synchronous(function, *args):
            return function(*args)

        with patch.object(webhook_module.asyncio, 'to_thread', synchronous):
            try:
                self.test_webhook_mirror_checks_run_outside_the_gateway_event_loop()
            except AssertionError as error:
                print('synchronous baseline assertion:', error)
                return
        self.fail('synchronous baseline unexpectedly released the heartbeat')


if __name__ == '__main__':
    unittest.main()
