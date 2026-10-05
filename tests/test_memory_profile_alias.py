# ABOUTME: Checks managed derivative tools through the Hermes profile's installed root alias.
# ABOUTME: Keeps the configured root alias while rejecting redirected child source directories.
import unittest
import shutil
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryService

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
        self.fixture.fixture.fixture.fixture.memory = NativeMemory(self.root)

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

    def test_system_source_accepts_root_alias_and_refuses_redirected_leaf(self):
        source = self.root / 'LIFEOS/ALGORITHM/Synthetic.md'
        source.parent.mkdir(parents=True)
        source.write_text('# Synthetic procedure\nUse the synthetic fixture.\n')
        delegation = self.fixture.fixture.fixture
        service = MemoryService(delegation.configuration)
        result = service.native(delegation.context, 'read_source', {'path': str(source)})
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['content'], source.read_text())
        foreign = self.root.parent / 'foreign-system-source.md'
        foreign.write_text('# Synthetic foreign procedure\n')
        source.unlink(); source.symlink_to(foreign)
        result = service.native(delegation.context, 'read_source', {'path': str(source)})
        self.assertFalse(result['ok'])
        self.assertNotIn('Synthetic foreign procedure', str(result))

    def test_profile_alias_does_not_admit_redirected_environment_or_consumer(self):
        foreign = self.root.parent / 'foreign-environment'
        foreign.write_text('SYNTHETIC_FOREIGN=preserved\n')
        self.fixture.fixture.env.unlink(); self.fixture.fixture.env.symlink_to(foreign)
        self.assertNotEqual(self.fixture.fixture.call().returncode, 0)
        self.assertEqual(foreign.read_text(), 'SYNTHETIC_FOREIGN=preserved\n')
        self.assertFalse(self.fixture.fixture.output.exists())
        self.fixture.fixture.env.unlink(); self.fixture.fixture.env.write_text('SYNTHETIC_KEEP=fixture\n')
        consumer = self.root / 'skills/_LIFEOS'
        consumer.rmdir(); consumer.symlink_to(self.root.parent)
        self.assertNotEqual(self.fixture.fixture.call('--dry-run').returncode, 0)
        self.assertFalse(self.fixture.fixture.output.exists())

    def redirect_root(self):
        replacement = self.root.parent / '.hermes-replacement'
        shutil.copytree(self.root.resolve(), replacement, symlinks=True)
        self.root.unlink(); self.root.symlink_to(replacement)
        return replacement

    def test_changed_root_binding_refuses_a_previous_derivative_plan(self):
        delegation = self.fixture.fixture.fixture
        service = MemoryService(delegation.configuration)
        plan = service.native(delegation.context, 'derived_sync_plan', {'args': ['--force']})
        self.assertTrue(plan['ok'], plan)
        self.redirect_root()
        result = service.native(delegation.context, 'derived_sync_check',
            {'args': ['--force'], 'signature': plan['signature']})
        self.assertFalse(result['ok'])
        self.assertFalse(self.fixture.state.exists())
        self.assertFalse(self.fixture.fixture.output.exists())

    def test_actual_root_change_after_hash_render_refuses_publication(self):
        original = NativeMemory._native
        rendered = []

        def native(memory, action, **arguments):
            result = original(memory, action, **arguments)
            if action == 'deny_hashes':
                rendered.append(result)
                self.redirect_root()
            return result

        delegation = self.fixture.fixture.fixture
        service = MemoryService(delegation.configuration)
        NativeMemory._native = native
        try:
            result = service.native(delegation.context, 'deny_hashes', {'args': ['--show-tokens']})
        finally:
            NativeMemory._native = original
        self.assertEqual(len(rendered), 1)
        self.assertIn('fixturesurname fixturegivenname', rendered[0]['tokens'])
        self.assertFalse(result['ok'])
        self.assertNotIn('fixturesurname fixturegivenname', str(result))
        self.assertEqual(self.fixture.fixture.env.read_text(), 'SYNTHETIC_KEEP=fixture\n')
        self.assertEqual((self.root.parent / '.hermes/.env').read_text(), 'SYNTHETIC_KEEP=fixture\n')
        self.assertFalse(self.fixture.fixture.output.exists())
