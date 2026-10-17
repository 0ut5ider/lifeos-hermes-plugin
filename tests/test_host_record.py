# ABOUTME: Checks the LifeOS host record and its retained original Hermes files.
# ABOUTME: Refuses malformed records, foreign originals directories, and changed originals.
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.host_record import (
    HostRecordRejected, build_record, check_originals, load_record, originals_path, record_path)


STOCK = "VALID_HOOKS = {'pre_tool_call'}\n"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class HostRecordTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.profile = Path(self.folder.name) / '.hermes'
        self.profile.mkdir(mode=0o700)
        self.entry = {'label': 'v0.0.1', 'commit': 'a' * 40, 'patches': [{'name': 'host.patch', 'sha256': 'b' * 64}],
                      'files': {'hermes_cli/plugins.py': {'stock': digest(STOCK), 'patched': 'c' * 64},
                                'hermes_cli/new_hook.py': {'stock': None, 'patched': 'd' * 64}}}
        self.record = build_record(self.profile, '/home/owner/.hermes/hermes-agent', self.entry,
                                   operation='e' * 32, version='0.8.0')

    def publish(self, value):
        record_path(self.profile).write_text(json.dumps(value))
        record_path(self.profile).chmod(0o600)

    def retain(self, text=STOCK):
        path = originals_path(self.profile) / 'hermes_cli/plugins.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o644)

    def test_round_trip_and_absence(self):
        self.assertIsNone(load_record(self.profile))
        self.publish(self.record)
        self.assertEqual(load_record(self.profile), self.record)

    def test_malformed_records_are_refused(self):
        for change in ({'format': 2}, {'source': 'relative/path'}, {'originals': '/elsewhere'},
                       {'operation': ''}, {'commit': 'short'}, {'extra': True}):
            with self.subTest(change=change):
                self.publish({**self.record, **change})
                with self.assertRaises(HostRecordRejected):
                    load_record(self.profile)

    def test_group_writable_record_is_refused(self):
        self.publish(self.record)
        record_path(self.profile).chmod(0o664)
        with self.assertRaises(HostRecordRejected):
            load_record(self.profile)

    def test_originals_are_verified_against_stock_hashes(self):
        self.retain()
        self.assertEqual(check_originals(self.record),
                         {'hermes_cli/plugins.py': originals_path(self.profile) / 'hermes_cli/plugins.py'})

    def test_changed_or_missing_original_is_refused(self):
        with self.assertRaisesRegex(HostRecordRejected, 'missing'):
            check_originals(self.record)
        self.retain(STOCK + '# edited\n')
        with self.assertRaisesRegex(HostRecordRejected, 'changed'):
            check_originals(self.record)

    def test_linked_original_is_refused(self):
        target = Path(self.folder.name) / 'elsewhere.py'
        target.write_text(STOCK)
        path = originals_path(self.profile) / 'hermes_cli/plugins.py'
        path.parent.mkdir(parents=True)
        os.symlink(target, path)
        with self.assertRaises(HostRecordRejected):
            check_originals(self.record)


if __name__ == '__main__':
    unittest.main()
