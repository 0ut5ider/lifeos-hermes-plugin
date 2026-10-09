# ABOUTME: Exercises LocalIntelligence refresh initiation through the native dashboard and selected owner command.
# ABOUTME: Requires current authenticated preparation and preserves missing-hometown refusal before effects.
import json
import os
from pathlib import Path
import unittest
import httpx
import test_memory_conduit_jobs as job_fixture


class MemoryLocalRefreshJobAuthenticationTests(unittest.TestCase):
    endpoint = '/api/plugins/lifeos-hook-bridge/memory/local_job'
    setUp = job_fixture.MemoryConduitJobAuthenticationTests.setUp
    activate = job_fixture.MemoryConduitJobAuthenticationTests.activate
    test_anonymous_job_preparation_requires_real_authentication = job_fixture.MemoryConduitJobAuthenticationTests.test_anonymous_job_preparation_requires_real_authentication
    test_owner_receives_only_a_current_configuration_restriction = job_fixture.MemoryConduitJobAuthenticationTests.test_owner_receives_only_a_current_configuration_restriction
    test_disabled_read_only_and_unbound_terminal_jobs_refuse_preparation = job_fixture.MemoryConduitJobAuthenticationTests.test_disabled_read_only_and_unbound_terminal_jobs_refuse_preparation


class MemoryLocalRefreshJobRelayTests(unittest.TestCase):
    native_module = 'local-intelligence.ts'
    create_fixture = job_fixture.MemoryConduitJobRelayTests.create_fixture
    native_module_name = job_fixture.MemoryConduitJobRelayTests.native_module_name
    stop_dashboard = job_fixture.MemoryConduitJobRelayTests.stop_dashboard
    stop_pulse = job_fixture.MemoryConduitJobRelayTests.stop_pulse
    login = job_fixture.MemoryConduitJobRelayTests.login
    def setUp(self):
        job_fixture.MemoryConduitJobRelayTests.setUp(self)
        (self.root / 'skills').mkdir(exist_ok=True)
        (self.root / 'skills/LocalIntelligence').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'skills/LocalIntelligence')


    def test_authenticated_native_refresh_starts_selected_owner_job(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.post(self.native + '/api/local-intelligence/refresh')
            self.assertEqual(response.status_code, 202, response.text)
            self.assertRegex(response.json()['run_id'], '^[-0-9TZ]+_[0-9a-f]{8}$')


class MemoryLocalRefreshJobCommandTests(unittest.TestCase):
    def setUp(self):
        self.fixture = job_fixture.MemoryConduitJobCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        root = self.fixture.fixture.native.root
        (root / 'skills').mkdir(exist_ok=True)
        (root / 'skills/LocalIntelligence').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'skills/LocalIntelligence')

    def test_actual_selected_profile_command_refuses_missing_hometown(self):
        result = self.fixture.fixture.call('local-intelligence')
        self.assertEqual((result.returncode, result.stderr), (1, ''), result.stdout)
        body = json.loads(result.stdout)
        self.assertEqual(body['status'], 'failed')
        self.assertEqual(body['exit_code'], 1)
        self.assertFalse((self.fixture.fixture.native.root / 'LIFEOS/MEMORY/DATA/LocalIntelligence').exists())
        self.assertEqual(self.fixture.fixture.fixture.fixture.received, [])
