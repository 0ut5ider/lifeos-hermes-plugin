# ABOUTME: Tests owner-facing memory status and controls against native synthetic records.
# ABOUTME: Keeps sharing explicit and verifies that diagnostics do not claim unfinished activation.
from pathlib import Path
import unittest

from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_sharing as sharing_fixture


class MemoryPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.fixture = sharing_fixture.MemorySharingTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.preferences = MemoryPreferences(self.fixture.fixture.config, self.fixture.fixture.fixture.root,
                                             self.fixture.keys, Path('/usr/bin/python3'),
                                             Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py')

    def test_missing_configuration_and_partial_setup_are_not_reported_active(self):
        self.fixture.fixture.config.unlink()
        missing = self.preferences.status()
        self.assertEqual(missing['state'], 'not_configured')
        self.assertFalse(missing['sharing_enabled'])
        self.assertFalse(missing['activation_ready'])
        self.assertIn('native_proposal_policy', missing['remaining_gates'])

    def test_health_reports_native_recall_without_enabling_ownership(self):
        self.fixture.fixture.fixture.remember()
        result = self.preferences.status()
        self.assertEqual(result['state'], 'prepared')
        self.assertEqual(result['native_health'], 'ok')
        self.assertEqual(result['active_facts'], 1)
        self.assertFalse(result['ownership_enabled'])
        self.assertEqual(result['automatic_review'], 'Native LifeOS hooks')
        self.assertFalse(result['proposal_review_available'])

    def test_owner_review_uses_current_native_records_and_strict_tool_arguments(self):
        saved = self.fixture.fixture.fixture.remember()
        result = self.preferences.review('lifeos_memory_search', {'query':'synthetic lab'})
        self.assertEqual(result['results'][0]['reference'], saved['reference'])
        result = self.preferences.review('lifeos_memory_forget', {'reference':saved['reference'], 'request_id':'owner-forget','dry_run':True})
        self.assertEqual(result['status'], 'rejected')
        result = self.preferences.review('lifeos_memory_forget', {'reference':saved['reference'], 'request_id':'owner-forget'})
        self.assertEqual(result['status'], 'committed')
        self.assertEqual(self.preferences.status()['active_facts'], 0)

    def test_sharing_disable_revokes_services_without_deleting_grants_or_facts(self):
        self.fixture.sharing.enroll('reader', sharing_fixture.public_key(52),projects=['lab'],model_route='unknown')
        saved = self.fixture.fixture.fixture.remember()
        self.preferences.sharing(False)
        config = MemoryConfiguration(self.fixture.fixture.config).load()
        self.assertIn('reader', config['clients'])
        self.assertEqual(self.fixture.fixture.service.call_client('reader','lifeos_memory_get',{'reference':saved['reference']})['status'],'rejected')
        self.assertEqual(self.preferences.review('lifeos_memory_get',{'reference':saved['reference']})['status'],'ok')
        with self.assertRaises(ValueError):
            self.preferences.sharing('yes')

    def test_configuration_for_another_installation_is_refused(self):
        config = MemoryConfiguration(self.fixture.fixture.config)
        config.update(lambda value:value.update(root=str(self.fixture.fixture.fixture.root.parent/'other')))
        self.assertEqual(self.preferences.status()['state'],'unavailable')
        with self.assertRaises(RuntimeError):
            self.preferences.sharing(True)


if __name__ == '__main__':
    unittest.main()
