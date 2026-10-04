# ABOUTME: Verifies coherent private backups of native facts and their governance metadata.
# ABOUTME: Uses actual native writes, retirement, process locks, and disposable recovery trees.
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lifeos_hook_bridge.memory_access import NativeMemory, MemoryUnavailable
from lifeos_hook_bridge.memory_backup import create, inspect
import test_memory_native as native_fixture


class MemoryBackupTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.destination = self.fixture.home / 'backups/native-one'
        self.saved = self.fixture.remember('Synthetic fact preserved by native backup', 'backup-original')

    def recover_fixture(self, manifest):
        directory = tempfile.TemporaryDirectory(prefix='native-backup-recovery-')
        self.addCleanup(directory.cleanup)
        home = Path(directory.name)
        root = home / '.claude'
        user = home / '.config/LIFEOS/USER'
        (root / 'LIFEOS').mkdir(parents=True)
        user.mkdir(parents=True)
        (root / 'LIFEOS/USER').symlink_to(user)
        (root / 'LIFEOS/MEMORY').symlink_to(user / 'MEMORY')
        (root / 'LIFEOS/TOOLS').symlink_to(native_fixture.SOURCE / 'LIFEOS/TOOLS')
        for entry in manifest['directories']:
            (user / entry['path']).mkdir(parents=True, exist_ok=True)
        for entry in manifest['files']:
            target = user / entry['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((self.destination / 'files' / str(entry['copy'])).read_bytes())
            target.chmod(entry['mode'])
        return NativeMemory(root)

    def test_snapshot_keeps_native_references_retirements_and_current_contents_together(self):
        retired = self.fixture.remember('Synthetic forgotten backup claim', 'backup-retired')
        self.fixture.memory.forget(native_fixture.OWNER, retired['reference'], 'backup-forget')
        hot = self.fixture.remember('RULE: synthetic private backup preference', 'backup-hot', 'principal')
        result = create(self.fixture.memory, native_fixture.OWNER, self.destination)
        self.assertEqual(result['status'], 'committed')
        manifest = inspect(self.fixture.memory, native_fixture.OWNER, self.destination, result['signature'])
        recovered = self.recover_fixture(manifest)
        self.assertEqual(recovered.get(native_fixture.OWNER, self.saved['reference'])['content'],
                         'Synthetic fact preserved by native backup')
        self.assertEqual(recovered.get(native_fixture.OWNER, hot['reference'])['content'],
                         'RULE: synthetic private backup preference')
        self.assertNotIn('Synthetic forgotten backup claim',
                         [row['content'] for row in recovered.recall(native_fixture.OWNER, 'forgotten backup claim')])
        self.assertEqual(recovered.get(native_fixture.OWNER, retired['reference'])['status'], 'conflict')
        with recovered._transaction() as connection:
            self.assertEqual(connection.execute('SELECT status FROM records WHERE id=?',
                             (retired['reference']['id'],)).fetchone()[0], 'forgotten')
        self.assertNotIn('Synthetic fact preserved', json.dumps(result))
        self.assertFalse(any(entry['path'].endswith('memory-access.lock') for entry in manifest['files']))

    def test_snapshot_copies_binary_sources_empty_directories_and_original_file_metadata(self):
        user = self.fixture.home / '.config/LIFEOS/USER'
        (user / 'synthetic-empty').mkdir()
        payload = user / 'synthetic-attachment.bin'
        data = bytes(range(256))
        payload.write_bytes(data)
        payload.chmod(0o640)
        create(self.fixture.memory, native_fixture.OWNER, self.destination)
        manifest = inspect(self.fixture.memory, native_fixture.OWNER, self.destination)
        entry = next(item for item in manifest['files'] if item['path'] == payload.name)
        self.assertEqual(entry['mode'], 0o640)
        self.assertEqual(entry['mtime_ns'], payload.stat().st_mtime_ns)
        self.assertEqual((self.destination / 'files' / str(entry['copy'])).read_bytes(), data)
        self.assertIn('synthetic-empty', [item['path'] for item in manifest['directories']])

    def test_snapshot_files_and_directories_have_private_permissions(self):
        create(self.fixture.memory, native_fixture.OWNER, self.destination)
        for path in [self.destination, *self.destination.rglob('*')]:
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600, path)

    def test_reader_cannot_collect_or_inspect_an_owner_backup(self):
        with self.assertRaisesRegex(MemoryUnavailable, 'owner'):
            create(self.fixture.memory, native_fixture.READER, self.destination)
        self.assertFalse(self.destination.exists())
        create(self.fixture.memory, native_fixture.OWNER, self.destination)
        with self.assertRaisesRegex(MemoryUnavailable, 'owner'):
            inspect(self.fixture.memory, native_fixture.READER, self.destination)

    def test_source_redirect_refuses_without_publishing_a_snapshot(self):
        user = self.fixture.home / '.config/LIFEOS/USER'
        (user / 'synthetic-redirect').symlink_to(self.fixture.home / 'external-secret')
        with self.assertRaisesRegex(MemoryUnavailable, 'physical path'):
            create(self.fixture.memory, native_fixture.OWNER, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.destination.parent.glob('.backup-*')), [])

    def test_existing_snapshot_and_redirected_destination_are_preserved(self):
        self.destination.parent.mkdir()
        external = self.fixture.home / 'synthetic-external'
        external.mkdir()
        self.destination.symlink_to(external)
        with self.assertRaises(MemoryUnavailable):
            create(self.fixture.memory, native_fixture.OWNER, self.destination)
        self.assertEqual(list(external.iterdir()), [])
        self.destination.unlink()
        create(self.fixture.memory, native_fixture.OWNER, self.destination)
        before = (self.destination / 'manifest.json').read_bytes()
        with self.assertRaises(MemoryUnavailable):
            create(self.fixture.memory, native_fixture.OWNER, self.destination)
        self.assertEqual((self.destination / 'manifest.json').read_bytes(), before)

    def test_integrity_and_installation_binding_refuse_modified_copies_or_metadata(self):
        result = create(self.fixture.memory, native_fixture.OWNER, self.destination)
        manifest = inspect(self.fixture.memory, native_fixture.OWNER, self.destination, result['signature'])
        copy = self.destination / 'files' / str(manifest['files'][0]['copy'])
        original = copy.read_bytes()
        copy.write_bytes(b'Synthetic changed recovery bytes')
        with self.assertRaisesRegex(MemoryUnavailable, 'integrity'):
            inspect(self.fixture.memory, native_fixture.OWNER, self.destination, result['signature'])
        copy.write_bytes(original)
        with self.assertRaisesRegex(MemoryUnavailable, 'installation'):
            inspect(self.fixture.memory, replace(native_fixture.OWNER, principal='other'), self.destination)
        manifest['files'][0]['path'] = '../synthetic-outside'
        (self.destination / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(MemoryUnavailable):
            inspect(self.fixture.memory, native_fixture.OWNER, self.destination)

    def test_concurrent_native_writer_produces_a_recoverable_consistent_snapshot(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            writer = executor.submit(self.fixture.remember, 'Synthetic concurrent backup claim', 'backup-concurrent')
            snapshot = executor.submit(create, self.fixture.memory, native_fixture.OWNER, self.destination)
            self.assertEqual(writer.result()['status'], 'committed')
            self.assertEqual(snapshot.result()['status'], 'committed')
        recovered = self.recover_fixture(inspect(self.fixture.memory, native_fixture.OWNER, self.destination))
        rows = recovered.recall(native_fixture.OWNER, 'backup')
        self.assertIn(self.saved['reference'], [row['reference'] for row in rows])
        with recovered._transaction() as connection:
            digests = {row['id']: row['digest'] for row in connection.execute('SELECT id, digest FROM records')}
        self.assertTrue(all(hashlib.sha256(row['content'].encode()).hexdigest() == digests[row['reference']['id']]
                            for row in rows))

    def test_changed_registered_content_cannot_be_reported_as_a_verified_backup(self):
        current = self.fixture.memory.get(native_fixture.OWNER, self.saved['reference'])
        rows = self.fixture.memory.recall(native_fixture.OWNER, current['content'])
        path = self.fixture.root / rows[0]['source']['path']
        path.write_text(path.read_text().replace(current['content'], 'Synthetic unregistered overwrite'))
        with self.assertRaises(MemoryUnavailable):
            create(self.fixture.memory, native_fixture.OWNER, self.destination)
        self.assertFalse(self.destination.exists())

    def test_unregistered_hot_entries_cannot_be_reported_as_coherent_governed_memory(self):
        self.fixture.remember('RULE: synthetic registered backup rule', 'backup-rule', 'principal')
        target = self.fixture.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'
        target.write_text(target.read_text().replace('<!-- END ENTRIES -->',
                          'RULE: synthetic unregistered backup rule\n<!-- END ENTRIES -->'))
        with self.assertRaises(MemoryUnavailable):
            create(self.fixture.memory, native_fixture.OWNER, self.destination)
        self.assertFalse(self.destination.exists())

    def test_process_death_before_publication_keeps_live_data_and_a_private_verifiable_stage(self):
        program = '''import os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
import lifeos_hook_bridge.memory_backup as backup
from test_memory_native import OWNER
publish = backup.publish
def stop_after_manifest(path, data):
    publish(path, data)
    if path.name == 'manifest.json':
        os._exit(84)
backup.publish = stop_after_manifest
backup.create(NativeMemory(Path(sys.argv[1])), OWNER, Path(sys.argv[2]))
'''
        result = subprocess.run([sys.executable, '-c', program, str(self.fixture.root), str(self.destination)],
                                env=dict(os.environ), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 84, result.stderr)
        self.assertEqual((result.stdout, result.stderr), ('', ''))
        self.assertFalse(self.destination.exists())
        pending = list(self.destination.parent.glob('.backup-*'))
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].stat().st_mode & 0o777, 0o700)
        inspected = inspect(self.fixture.memory, native_fixture.OWNER, pending[0])
        self.assertEqual(inspected['schema'], 4)
        self.assertEqual(self.fixture.memory.get(native_fixture.OWNER, self.saved['reference'])['status'], 'ok')
        self.assertEqual(create(self.fixture.memory, native_fixture.OWNER, self.destination)['status'], 'committed')
