# ABOUTME: Review diagnostic for native origin lookup used by the send tool mirror.
# ABOUTME: Shows whether the PR34 fixture session is discoverable without an explicit session.
import logging
import unittest

import test_discord_notification_mirror as base


class FindSessionReview(base.DiscordNotificationMirrorTests):
    def test_review_origin_lookup(self):
        from gateway.mirror import _find_session_id
        from hermes_state_registry import acquire, release_or_close
        print('find (no user)', _find_session_id('discord', '60'))
        print('find (user 20)', _find_session_id('discord', '60', user_id='20'))
        db = acquire()
        try:
            print('db path', getattr(db, 'db_path', None), 'store db path', getattr(self.db, 'db_path', None))
        finally:
            release_or_close(db)


for name in list(vars(base.DiscordNotificationMirrorTests)):
    if name.startswith('test_'):
        setattr(FindSessionReview, name, None)
del base.DiscordNotificationMirrorTests
