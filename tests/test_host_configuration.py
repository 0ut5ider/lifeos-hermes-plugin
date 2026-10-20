# ABOUTME: Checks the record of LifeOS configuration changes and the restore of only those recorded values.
# ABOUTME: Protected settings such as the model and messaging platforms must never change.
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.host_configuration import (
    ABSENT, RECORD, ConfigurationConflict, changed_paths, check_memory_provider, check_preserved, record, record_restored,
    restore, restore_operation)
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


STOCK = b'model:\n  default: m1\nplatforms:\n  discord:\n    enabled: true\nskills:\n  external_dirs: []\n'
INSTALLED = (b'model:\n  default: m1\nplatforms:\n  discord:\n    enabled: true\nskills:\n  external_dirs: [/c/skills]\n'
             b'approvals:\n  mode: manual\nplugins:\n  enabled: [lifeos-hook-bridge]\n')


class HostConfigurationTests(unittest.TestCase):
    def test_changed_leaf_values_are_listed(self):
        from ruamel.yaml import YAML
        before, after = YAML(typ='safe').load(STOCK), YAML(typ='safe').load(INSTALLED)
        self.assertEqual([path for path, _, _ in changed_paths(before, after)],
                         [('approvals',), ('plugins',), ('skills', 'external_dirs')])

    def test_protected_settings_must_not_change(self):
        check_preserved(STOCK, INSTALLED)
        with self.assertRaisesRegex(ReleaseRejected, 'model.default'):
            check_preserved(STOCK, INSTALLED.replace(b'default: m1', b'default: m2'))
        with self.assertRaisesRegex(ReleaseRejected, 'platforms.discord.enabled'):
            check_preserved(STOCK, INSTALLED.replace(b'enabled: true', b'enabled: false'))

    def test_memory_provider_must_not_change_unless_the_operation_owns_it(self):
        builtin = INSTALLED + b'memory:\n  provider: builtin\n'
        check_memory_provider(builtin, builtin, owned=False)
        for after in (INSTALLED + b'memory:\n  provider: lifeos\n', INSTALLED, INSTALLED + b'memory: {}\n'):
            with self.subTest(after=after), self.assertRaisesRegex(ReleaseRejected, 'memory.provider'):
                check_memory_provider(builtin, after, owned=False)
        check_memory_provider(builtin, INSTALLED + b'memory:\n  provider: lifeos\n', owned=True)
        check_memory_provider(INSTALLED, INSTALLED + b'memory:\n  enabled: true\n', owned=False)

    def test_record_keeps_the_earliest_before_value_and_skips_owned_plugin_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            first = record(profile, STOCK, INSTALLED)
            self.assertEqual(first['values'], [
                {'path': ['approvals'], 'before': ABSENT, 'installed': {'mode': 'manual'}},
                {'path': ['skills', 'external_dirs'], 'before': [], 'installed': ['/c/skills']}])
            later = INSTALLED.replace(b'mode: manual', b'mode: smart')
            second = record(profile, INSTALLED, later)
            self.assertEqual(second['values'][0], {'path': ['approvals'], 'before': ABSENT, 'installed': {'mode': 'smart'}})

    def test_a_rolled_back_configuration_becomes_the_installed_value_of_each_recorded_path(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            (profile / 'config.yaml').write_bytes(STOCK)
            self.assertIsNone(record_restored(profile))
            self.assertFalse((profile / RECORD).exists())
            record(profile, STOCK, INSTALLED)
            restored = record_restored(profile)
            self.assertEqual(restored['values'], [
                {'path': ['approvals'], 'before': ABSENT, 'installed': ABSENT},
                {'path': ['skills', 'external_dirs'], 'before': [], 'installed': []}])

    def test_restore_returns_recorded_values_and_reports_later_owner_edits(self):
        recorded = {'values': [{'path': ['approvals'], 'before': ABSENT, 'installed': {'mode': 'manual'}},
                               {'path': ['skills', 'external_dirs'], 'before': [], 'installed': ['/c/skills']}]}
        current = {'approvals': {'mode': 'manual'}, 'skills': {'external_dirs': ['/c/skills', '/owner/extra']},
                   'model': {'default': 'm9'}}
        restored, conflicts = restore(current, recorded)
        self.assertNotIn('approvals', restored)
        self.assertEqual(restored['skills']['external_dirs'], ['/c/skills', '/owner/extra'])
        self.assertEqual(restored['model'], {'default': 'm9'})
        self.assertEqual(conflicts, ['skills.external_dirs'])


    def test_operation_restore_keeps_later_owner_changes_and_returns_the_changed_values(self):
        before = b'# owner notes\nmodel:\n  default: m1\nplugins:\n  enabled: [other]\n  entries:\n    lifeos-hook-bridge:\n      settings:\n        lifeos_source_dir: /old\n'
        after = before.replace(b'/old', b'/new').replace(b'[other]', b'[other, lifeos-hook-bridge]')
        self.assertEqual(restore_operation(before, after, after), before)
        later = after.replace(b'default: m1', b'default: m2')
        restored = restore_operation(before, after, later)
        self.assertIn(b'# owner notes', restored)
        self.assertEqual(restored, before.replace(b'default: m1', b'default: m2'))

    def test_operation_restore_removes_values_the_operation_added(self):
        before = b'model:\n  default: m1\n'
        after = before + b'approvals:\n  mode: manual\n'
        self.assertEqual(restore_operation(before, after, after.replace(b'm1', b'm2')), b'model:\n  default: m2\n')

    def test_operation_restore_refuses_a_value_the_owner_changed_again(self):
        before = b'model:\n  default: m1\nplugins:\n  enabled: [other]\n'
        after = before.replace(b'[other]', b'[other, lifeos-hook-bridge]')
        later = after.replace(b'lifeos-hook-bridge]', b'lifeos-hook-bridge, extra]')
        with self.assertRaisesRegex(ConfigurationConflict, r'plugins\.enabled') as raised:
            restore_operation(before, after, later)
        self.assertIsInstance(raised.exception, ReleaseRejected)
        self.assertIn('then restore again', str(raised.exception))


    def test_operation_restore_refuses_a_configuration_that_cannot_be_read(self):
        before = b'model:\n  default: m1\n'
        after = before + b'approvals:\n  mode: manual\n'
        later = after + b'model:\n  default: m2\n'
        with self.assertRaisesRegex(ReleaseRejected, 'config.yaml cannot be read'):
            restore_operation(before, after, later)

if __name__ == '__main__':
    unittest.main()
