# ABOUTME: Tests native PULSE remount through real authenticated dashboard HTTP sessions.
# ABOUTME: Exercises native preparation, publication, owner revocation, and connector refusal.
import shutil
import unittest
import httpx

import test_memory_admin_dashboard as dashboard_tests
from test_memory_native import SOURCE
import test_memory_pulse_relay as relay_tests


class MemoryRemountRelayTests(unittest.TestCase):
    native_module = 'hermes.ts'
    setUp = relay_tests.MemoryPulseRelayTests.setUp
    stop_dashboard = relay_tests.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_tests.MemoryPulseRelayTests.stop_pulse
    native_module_name = relay_tests.MemoryPulseRelayTests.native_module_name
    login = relay_tests.MemoryPulseRelayTests.login

    def create_fixture(self):
        fixture = dashboard_tests.MemoryAdminDashboardTests()
        fixture.home = None
        original = fixture.setUp
        def setup():
            original()
            fixture.home = fixture.fixture.root.parent
            shutil.copytree(SOURCE / 'LIFEOS/PULSE', fixture.fixture.root / 'LIFEOS/PULSE')
        fixture.setUp = setup
        return fixture

    def test_remount_requires_incoming_authenticated_owner_and_preserves_native_output(self):
        path = self.native + '/api/hermes/remount'
        response = httpx.post(path)
        self.assertEqual(response.status_code, 401, response.text)
        self.assertFalse((self.fixture.fixture.profile / 'SOUL.md').exists())
        with httpx.Client(timeout=60) as client:
            self.login(client)
            response = client.post(path)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertTrue(response.json()['ok'])
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertIn('SyntheticSafetyDoctrine', (self.fixture.fixture.profile / 'SOUL.md').read_text())
            self.assertEqual(self.fixture.grants(), [])
            self.fixture.configuration.update(lambda config:config['accounts'].pop(self.fixture.account))
            self.assertEqual(client.post(path).status_code, 403)

    def test_remount_refuses_cross_origin_body_and_query_before_publication(self):
        with httpx.Client(timeout=60) as client:
            self.login(client)
            path = self.native + '/api/hermes/remount'
            for url, options, status in [(path, {'headers':{'Origin':'https://other.invalid'}}, 403),
                (path+'?home=other', {}, 400), (path, {'json':{'account':self.fixture.account}}, 400)]:
                with self.subTest(url=url, status=status):
                    response = client.post(url, **options)
                    self.assertEqual(response.status_code, status, response.text)
            self.assertFalse((self.fixture.fixture.profile / 'SOUL.md').exists())

    def test_connector_loss_cannot_fall_back_to_raw_native_mount(self):
        with httpx.Client(timeout=60) as client:
            self.login(client)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.post(self.native+'/api/hermes/remount')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertFalse((self.fixture.fixture.profile / 'SOUL.md').exists())


if __name__ == '__main__':
    unittest.main()
