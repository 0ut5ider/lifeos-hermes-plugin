# ABOUTME: Checks the record of LifeOS configuration changes and the restore of only those recorded values.
# ABOUTME: Protected settings such as the model and messaging platforms must never change.
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.host_configuration import (
    ABSENT, changed_paths, check_memory_provider, check_preserved, record, restore)
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


if __name__ == '__main__':
    unittest.main()
