# ABOUTME: Checks managed derivative tools through the Hermes profile's installed root alias.
# ABOUTME: Keeps the configured root alias while rejecting redirected child source directories.
import unittest

import test_memory_derived_sync as sync_fixture


class MemoryProfileAliasTests(unittest.TestCase):
    def setUp(self):
        self.fixture = sync_fixture.MemoryDerivedSyncTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        profile = self.root.parent / '.hermes'
        self.root.rename(profile)
        self.root.symlink_to(profile)

    def test_owner_can_plan_and_publish_through_the_installed_profile_alias(self):
        result = self.fixture.successful('--dry-run')
        self.assertIn('changed: 3', result.stdout)
        self.fixture.successful('--force')
        self.assertTrue(self.fixture.state.exists())
        self.assertTrue(self.fixture.fixture.output.exists())
        self.assertEqual(self.fixture.successful().stdout, '')

    def test_owner_hash_review_and_publication_accept_the_installed_profile_alias(self):
        result = self.fixture.fixture.successful('--dry-run', '--show-tokens')
        self.assertIn('fixturesurname fixturegivenname', result.stdout)
        self.fixture.fixture.successful()
        self.assertTrue(self.fixture.fixture.output.exists())

    def test_profile_alias_does_not_admit_a_redirected_pulse_directory(self):
        foreign = self.root.parent / 'foreign-pulse'
        foreign.mkdir()
        (self.root / 'LIFEOS/PULSE').symlink_to(foreign)
        self.assertNotEqual(self.fixture.call('--dry-run').returncode, 0)
        self.assertFalse(self.fixture.state.exists())
