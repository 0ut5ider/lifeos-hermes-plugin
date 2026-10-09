# ABOUTME: Exercises recoverable native LocalIntelligence digest publication with synthetic owner data.
# ABOUTME: Preserves dated history, latest copies, no-clobber behavior, and later source changes.
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from pathlib import Path
from dataclasses import asdict
import unittest
import test_memory_local_refresh as fixture
from lifeos_hook_bridge.memory_local_intelligence import PRIMARY, FALLBACK, HISTORY

SECTIONS = ('construction', 'crime', 'business', 'officials', 'legislation', 'elections', 'arrests', 'news')


class MemoryLocalRefreshPublicationTests(unittest.TestCase):
    setUp = fixture.MemoryLocalRefreshTests.setUp
    call = fixture.MemoryLocalRefreshTests.call

    def digest(self, *, populated=True):
        value = {'meta': {'city': 'SyntheticCity', 'state': 'TX', 'county': 'Synthetic', 'zip': '78701',
            'generated_at': datetime.now(timezone.utc).isoformat(), 'sources_used': ['news'] if populated else [],
            'sources_failed': [], 'errors': []}}
        value.update({key: {'items': [], 'source_status': 'empty'} for key in SECTIONS})
        if populated:
            value['news'] = {'items': [{'title': 'Synthetic local publication', 'source': 'synthetic',
                'url': 'https://synthetic.invalid/story', 'date': datetime.now(timezone.utc).date().isoformat()}],
                'source_status': 'ok'}
        return value

    def prepare(self):
        result = self.call()
        self.assertTrue(result['ok'], result)
        return result

    def publish(self, prepared, value):
        return self.call('local_refresh_publish', signature=prepared['signature'], value=value)

    def dated(self, prepared):
        return self.root / HISTORY / (prepared['plan']['date'] + '_syntheticcity_tx_digest.json')

    def test_current_native_digest_publishes_three_private_files(self):
        prepared = self.prepare()
        value = self.digest()
        result = self.publish(prepared, value)
        self.assertTrue(result['ok'], result)
        for path in (self.dated(prepared), self.root / PRIMARY, self.root / FALLBACK):
            self.assertEqual(json.loads(path.read_text()), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(result['summary']['latestSkipped'])

    def test_empty_run_preserves_populated_native_latest_copies(self):
        for relative in (PRIMARY, FALLBACK):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.digest()))
        before = [(self.root / relative).read_bytes() for relative in (PRIMARY, FALLBACK)]
        prepared = self.prepare()
        value = self.digest(populated=False)
        result = self.publish(prepared, value)
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['summary']['latestSkipped'])
        self.assertEqual([path.read_bytes() for path in (self.root / PRIMARY, self.root / FALLBACK)], before)
        self.assertEqual(json.loads(self.dated(prepared).read_text()), value)

    def test_later_native_latest_edit_and_owner_revocation_refuse_publication(self):
        prepared = self.prepare()
        path = self.root / PRIMARY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.digest(populated=False)))
        before = path.read_bytes()
        result = self.publish(prepared, self.digest())
        self.assertFalse(result['ok'], result)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(self.dated(prepared).exists())
        self.configuration.update(lambda value: value['accounts'].clear())
        self.assertFalse(self.publish(prepared, self.digest())['ok'])

    def test_private_generated_text_wrong_city_and_undeclared_fields_refuse(self):
        prepared = self.prepare()
        for mode in ('private', 'city', 'fields'):
            with self.subTest(mode=mode):
                value = self.digest()
                if mode == 'private': value['news']['items'][0]['title'] = '<private>SyntheticLocalHidden</private>'
                elif mode == 'city': value['meta']['city'] = 'OtherCity'
                else: value['caller_target'] = '/other'
                result = self.publish(prepared, value)
                self.assertFalse(result['ok'], result)
                self.assertFalse(self.dated(prepared).exists())

    def test_actual_render_changes_and_partial_publication_recovery(self):
        identity = self.identity.read_bytes()
        for mode in ('source', 'destination', 'authority', 'interrupt'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_local_refresh_process.py')),
                    str(self.configuration.path), mode, json.dumps(asdict(self.owner.context)), json.dumps(self.digest())],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.stderr, '')
                if mode == 'interrupt':
                    self.assertEqual(result.returncode, 73, result.stdout)
                    paths = list((self.root / HISTORY).glob('*_digest.json'))
                    self.assertEqual(len(paths), 1)
                    self.prepare()
                    self.assertEqual(list((self.root / HISTORY).glob('*_digest.json')), [])
                    self.assertFalse((self.root / PRIMARY).exists())
                    self.assertFalse((self.root / FALLBACK).exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertFalse(json.loads(result.stdout)['ok'])
                    self.assertFalse((self.root / FALLBACK).exists())
                    if mode == 'destination':
                        path = self.root / PRIMARY
                        self.assertTrue(json.loads(path.read_text())['synthetic_later'])
                        path.unlink()
                self.identity.write_bytes(identity)
                self.configuration.update(lambda config: config['accounts'].update({'chat-a:100': 'owner'}))
