# ABOUTME: Checks native freshness cache publication through the actual CLI.
# ABOUTME: Preserves previous artifacts when owner write authority or publication paths are unavailable.
import json
import os
import subprocess
from pathlib import Path
import sys
import unittest

import test_memory_freshness as freshness_fixture


class MemoryFreshnessCacheTests(unittest.TestCase):
    def setUp(self):
        self.fixture = freshness_fixture.MemoryFreshnessTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.cache = self.root / 'LIFEOS/USER/CACHE/freshness.json'

    def call(self, *args, context=True):
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/FreshnessCache.ts'), *args],
            env=self.fixture.environment(context=context), capture_output=True, text=True, timeout=30)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def previous(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text('{"synthetic_previous":"preserved"}')
        return self.cache.read_bytes()

    def test_owner_cache_and_print_keep_native_payload_fields(self):
        self.successful('--quiet')
        actual = json.loads(self.cache.read_text())
        printed = json.loads(self.successful('--print').stdout)
        self.assertEqual(actual['total'], 8)
        actual.pop('generated_at'); printed.pop('generated_at')
        self.assertEqual(actual, printed)
        self.assertEqual({row['slug'] for row in actual['files']},
            {'telos', 'da_identity', 'principal_identity', 'projects', 'lifeos_system_prompt',
             'principal_telos', 'architecture_summary', 'lifeos_system_architecture'})

    def test_owner_and_standalone_cache_bytes_match_except_generation_clock(self):
        self.successful('--quiet')
        actual = json.loads(self.cache.read_text())
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.call('--quiet', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        native = json.loads(self.cache.read_text())
        actual.pop('generated_at'); native.pop('generated_at')
        self.assertEqual(actual, native)

    def test_owner_read_without_write_preserves_previous_cache(self):
        before = self.previous()
        self.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        result = self.call('--quiet')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.cache.read_bytes(), before)

    def test_missing_context_preserves_previous_cache(self):
        before = self.previous()
        self.assertNotEqual(self.call('--quiet', context=False).returncode, 0)
        self.assertEqual(self.cache.read_bytes(), before)

    def test_missing_context_does_not_create_a_publication_directory(self):
        self.assertFalse(self.cache.parent.exists())
        self.assertNotEqual(self.call('--quiet', context=False).returncode, 0)
        self.assertFalse(self.cache.parent.exists())

    def test_revocation_preserves_previous_cache(self):
        before = self.previous()
        self.fixture.fixture.configuration.update(lambda c: c['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call('--quiet').returncode, 0)
        self.assertEqual(self.cache.read_bytes(), before)

    def test_successful_publication_has_private_permissions(self):
        self.successful('--quiet')
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)

    def test_foreign_cache_directory_refuses_before_modifying_foreign_files(self):
        directory = self.fixture.fixture.fixture.home / 'foreign-cache'
        directory.mkdir()
        path = directory / 'freshness.json'
        path.write_text('{"synthetic_foreign":"preserved"}')
        self.cache.parent.symlink_to(directory)
        self.assertNotEqual(self.call('--quiet').returncode, 0)
        self.assertEqual(path.read_text(), '{"synthetic_foreign":"preserved"}')

    def test_registry_alias_refuses_before_recoverable_publication(self):
        memory = self.fixture.memory
        self.fixture.fixture.fixture.remember('Synthetic cache registry guard', 'cache-alias')
        self.cache.parent.mkdir()
        os.link(memory.database, self.cache)
        self.assertNotEqual(self.call('--quiet').returncode, 0)
        self.assertTrue(self.cache.samefile(memory.database))

    def process(self, mode, relative):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_freshness_write_process.py')),
            str(self.fixture.fixture.configuration.path), mode, 'freshness_cache', relative],
            env=self.fixture.environment(), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stderr, '')
        return result

    def test_source_change_after_render_preserves_cache_and_later_input(self):
        before = self.previous()
        relative = 'LIFEOS/USER/TELOS/TELOS.md'
        source = self.root / relative
        expected = source.read_text() + '\nSynthetic later source edit\n'
        result = self.process('source', relative)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        with self.fixture.memory._transaction():
            self.assertEqual(self.cache.read_bytes(), before)
        self.assertEqual(source.read_text(), expected)

    def test_owner_change_after_render_preserves_previous_cache(self):
        before = self.previous()
        result = self.process('authority', 'LIFEOS/USER/CACHE/freshness.json')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        with self.fixture.memory._transaction():
            self.assertEqual(self.cache.read_bytes(), before)

    def test_process_death_recovers_previous_cache(self):
        before = self.previous()
        result = self.process('interrupt', 'LIFEOS/USER/CACHE/freshness.json')
        self.assertEqual(result.returncode, 73)
        self.assertNotEqual(self.cache.read_bytes(), before)
        journal = self.fixture.memory.transaction.journal
        self.assertTrue(journal.exists())
        self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
        with self.fixture.memory._transaction():
            self.assertEqual(self.cache.read_bytes(), before)
        self.assertFalse(journal.exists())
        self.successful('--quiet')

    def test_process_death_removes_uncommitted_first_cache(self):
        result = self.process('interrupt', 'LIFEOS/USER/CACHE/freshness.json')
        self.assertEqual(result.returncode, 73)
        self.assertTrue(self.cache.exists())
        with self.fixture.memory._transaction():
            self.assertFalse(self.cache.exists())
        self.successful('--quiet')

    def test_read_only_print_does_not_publish_or_create_directory(self):
        self.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        printed = json.loads(self.successful('--print').stdout)
        self.assertEqual(printed['total'], 8)
        self.assertFalse(self.cache.parent.exists())

    def test_missing_connector_durable_marker_refuses_cache_publication(self):
        before = self.previous()
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertNotEqual(self.call('--quiet', context=False).returncode, 0)
        self.assertEqual(self.cache.read_bytes(), before)
