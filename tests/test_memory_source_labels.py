# ABOUTME: Checks excluded source filenames in adoption and current owner responses.
# ABOUTME: Uses native memory with ownership and external sharing disabled.
import json
import os
from pathlib import Path
import sys
import unittest

from lifeos_hook_bridge.memory_canonical import corpus
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native_fixture
from test_memory_native import OWNER


class MemorySourceLabelTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.memory
        self.root = self.fixture.root
        (self.root / 'LIFEOS/PULSE').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE']) / 'LIFEOS/PULSE')
        profile = self.fixture.home / 'hermes'; profile.mkdir(mode=0o700)
        self.configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
        self.configuration.save({'version': 1, 'root': str(self.root), 'principal': 'owner',
            'ownership_enabled': False, 'sharing_enabled': False,
            'accounts': {'dashboard:synthetic-owner': 'owner'}, 'destinations': {}, 'clients': {}})
        self.preferences = MemoryPreferences(self.configuration.path, self.root,
            self.fixture.home / '.ssh/authorized_keys', Path(sys.executable), self.fixture.home / 'unused-program')

    def note(self, name, title='Safe synthetic title'):
        path = self.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research' / (name + '.md')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\ntitle: ' + title + '\ntype: research\ncreated: 2026-10-02T00:00:00Z\n'
                        'updated: 2026-10-02T00:00:00Z\n---\n\nSafeSyntheticCurrentBody\n')
        return path

    def retire(self):
        saved = self.fixture.remember('RULE: Synthetic retired source label', 'label-save', 'principal')
        self.assertEqual(self.memory.forget(OWNER, saved['reference'], 'label-forget')['status'], 'committed')

    def test_private_filename_and_metadata_are_excluded_from_adoption(self):
        self.note('<private>SYNTHETIC_PRIVATE_LABEL')
        self.note('safe-name', '<private>SYNTHETIC_PRIVATE_TITLE')
        preview = self.preferences.preview_adoption(account='dashboard:synthetic-owner')
        self.assertEqual(preview['records'], [])
        self.assertNotIn('SYNTHETIC_PRIVATE', json.dumps(preview))
        receipt = self.preferences.adopt({'signature': preview['signature'], 'projects': {},
            'request_id': 'exclude-labels'}, account='dashboard:synthetic-owner')
        self.assertEqual(receipt['status'], 'committed')
        self.assertEqual(receipt['facts_adopted'], 0)

    def test_forgotten_filename_is_excluded_from_adoption(self):
        self.retire()
        self.note('Synthetic_retired_source_label')
        preview = self.preferences.preview_adoption(account='dashboard:synthetic-owner')
        self.assertEqual(preview['records'], [])
        self.assertNotIn('Synthetic_retired_source_label', json.dumps(preview))

    def test_early_body_rejection_does_not_expose_a_private_filename(self):
        self.retire()
        path = self.note('<private>SYNTHETIC_PRIVATE_REJECTED_LABEL')
        path.write_text(path.read_text().replace('SafeSyntheticCurrentBody', 'Synthetic retired source label'))
        preview = self.preferences.preview_adoption(account='dashboard:synthetic-owner')
        self.assertEqual(preview['records'], [])
        self.assertTrue(preview['excluded'])
        self.assertNotIn('SYNTHETIC_PRIVATE_REJECTED_LABEL', json.dumps(preview))

    def test_previously_registered_private_sources_do_not_enter_owner_responses(self):
        path = self.note('<private>SYNTHETIC_PRIVATE_LABEL')
        self.assert_registered_source_excluded(path, 'SYNTHETIC_PRIVATE_LABEL')

    def test_previously_registered_forgotten_labels_do_not_enter_owner_responses(self):
        self.retire()
        path = self.note('Synthetic_retired_source_label')
        self.assert_registered_source_excluded(path, 'Synthetic_retired_source_label')

    def assert_registered_source_excluded(self, path, marker):
        # A persisted registration represents adoption before source-label admission.
        with self.memory._transaction() as connection:
            self.memory._record(connection, OWNER, path, 'SafeSyntheticCurrentBody', 'project', 'lab',
                                {'kind': 'adopted'})
        canonical = corpus(self.memory, OWNER, str(self.root / 'LIFEOS/MEMORY'))
        self.assertEqual(canonical['records'], [])
        knowledge, _ = self.preferences.knowledge_response('/api/knowledge', account='dashboard:synthetic-owner')
        self.assertEqual(knowledge['body']['totalNotes'], 0)
        search = self.preferences.review('lifeos_memory_search', {'query': 'SafeSyntheticCurrentBody'},
                                         account='dashboard:synthetic-owner')
        self.assertEqual(search['results'], [])
        self.assertNotIn(marker, json.dumps([canonical, knowledge, search]))
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertFalse(self.configuration.load()['sharing_enabled'])
