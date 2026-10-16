# ABOUTME: Review checks for PR34 mirrors after compression rotation and session reset.
# ABOUTME: Uses the PR34 fixture with actual runtime rotation and the native mirror.
import unittest

import test_discord_notification_mirror as base


class LineageMirrorReview(base.DiscordNotificationMirrorTests):
    def test_review_compression_child_keeps_mirror(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        self.new_session('compressed-child')
        self.fixture.runtime.rotate_session('compressed-child', 'notification-session',
            metadata=self.metadata('compressed-child'))
        mirrored = self.mirror('compressed-child')
        print('compression child mirror', mirrored)
        self.assertTrue(mirrored)

    def test_review_reset_successor_refuses_mirror_and_admits_first_turn(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        self.new_session('reset-successor')
        mirrored = self.mirror('reset-successor')
        print('reset successor mirror', mirrored, self.store.load_transcript('reset-successor'))
        self.assertFalse(mirrored)
        self.fixture.runtime.admit(self.metadata('reset-successor'), **self.fixture.route, is_first_turn=True)
        self.assertTrue(self.mirror('reset-successor'))


for name in list(vars(base.DiscordNotificationMirrorTests)):
    if name.startswith('test_'):
        setattr(LineageMirrorReview, name, None)
if __name__ == '__main__':
    unittest.main()


class SendToolMirrorReview(base.DiscordNotificationMirrorTests):
    def test_review_send_tool_mirror_resolves_and_refuses_unadmitted_session(self):
        from tools.send_message_tool import _mirror_sent_message
        from gateway.config import Platform
        from gateway.session import SessionSource
        entry = self.store.get_or_create_session(SessionSource(platform=Platform.DISCORD, chat_id='60',
            chat_type='group', user_id='20', scope_id='10'))
        self.session = entry.session_id
        print('gateway session', self.session)
        mirrored = _mirror_sent_message('discord', '60', 'Synthetic morning notice', None)
        print('send tool unadmitted mirror', mirrored, self.store.load_transcript(self.session))
        self.assertFalse(mirrored)
        self.fixture.runtime.admit(self.metadata(self.session),
            **self.fixture.route, is_first_turn=True)
        mirrored = _mirror_sent_message('discord', '60', 'Synthetic morning notice', None)
        print('send tool admitted mirror', mirrored, len(self.store.load_transcript(self.session)))
        self.assertTrue(mirrored)


for name in list(vars(base.DiscordNotificationMirrorTests)):
    if name.startswith('test_'):
        setattr(SendToolMirrorReview, name, None)
del base.DiscordNotificationMirrorTests
