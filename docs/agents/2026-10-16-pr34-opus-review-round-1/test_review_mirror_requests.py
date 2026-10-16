# ABOUTME: Review measurement of Discord audience requests made by one mirror policy decision.
# ABOUTME: Uses the PR34 fixture HTTP server and the actual native mirror.
import time
import unittest

import test_discord_notification_mirror as base


class MirrorRequestReview(base.DiscordNotificationMirrorTests):
    def test_review_requests_per_mirror(self):
        self.fixture.runtime.admit(self.metadata('notification-session'),
            **self.fixture.route, is_first_turn=True)
        del self.audience.requests[:]
        started = time.perf_counter()
        self.assertTrue(self.mirror())
        print('synchronous mirror audience requests', list(self.audience.requests),
              'seconds', round(time.perf_counter() - started, 3))


for name in list(vars(base.DiscordNotificationMirrorTests)):
    if name.startswith('test_'):
        setattr(MirrorRequestReview, name, None)
del base.DiscordNotificationMirrorTests
