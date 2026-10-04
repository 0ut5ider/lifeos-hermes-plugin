# ABOUTME: Reconstructs complete native backups in separate owner recovery trees with actual native readers.
# ABOUTME: Verifies stable references, retained retirements, original-store preservation, and refused targets.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_access import NativeMemory, MemoryUnavailable
from lifeos_hook_bridge.memory_backup import create
from lifeos_hook_bridge.memory_backup_recovery import recover
import test_memory_native as native_fixture


class MemoryBackupRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.saved = self.fixture.remember('Synthetic complete native recovery fact', 'recovery-original')
        self.backup = self.fixture.home / 'backups/recovery-one'
        self.destination = self.fixture.home / 'recovery/native-one'

    def snapshot(self):
        return create(self.fixture.memory, native_fixture.OWNER, self.backup)['signature']

    def recover(self, signature):
        return recover(self.fixture.memory, native_fixture.OWNER, self.backup, signature, self.destination)

    def test_recovery_reconstructs_references_retirements_binary_sources_and_empty_directories(self):
        hot = self.fixture.remember('RULE: synthetic native recovery preference', 'recovery-hot', 'principal')
        retired = self.fixture.remember('Synthetic retired recovery claim', 'recovery-retired')
        self.fixture.memory.forget(native_fixture.OWNER, retired['reference'], 'recovery-forget')
        user = self.fixture.home / '.config/LIFEOS/USER'
        (user / 'empty-recovery-source').mkdir()
        attachment = user / 'recovery-payload.bin'
        attachment.write_bytes(bytes(range(256)))
        attachment.chmod(0o640)
        mtime = attachment.stat().st_mtime_ns
        result = self.recover(self.snapshot())
        self.assertEqual(result['status'], 'recovered', result)
        self.assertFalse(result['ownership_enabled'])
        recovered = NativeMemory(Path(result['root']))
        self.assertEqual(recovered.get(native_fixture.OWNER, self.saved['reference'])['content'],
                         'Synthetic complete native recovery fact')
        self.assertEqual(recovered.get(native_fixture.OWNER, hot['reference'])['content'],
                         'RULE: synthetic native recovery preference')
        self.assertEqual(recovered.get(native_fixture.OWNER, retired['reference'])['status'], 'conflict')
        copied = self.destination / '.config/LIFEOS/USER/recovery-payload.bin'
        self.assertEqual(copied.read_bytes(), bytes(range(256)))
        self.assertEqual(copied.stat().st_mode & 0o777, 0o640)
        self.assertEqual(copied.stat().st_mtime_ns, mtime)
        self.assertTrue((copied.parent / 'empty-recovery-source').is_dir())
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
        self.assertNotIn('Synthetic complete native recovery fact', json.dumps(result))
        self.assertFalse((self.destination / 'lifeos-memory.json').exists())
        recovery = json.loads(Path(result['recovery_manifest']).read_text())
        self.assertEqual(recovery['source_root'], str(self.fixture.root))
        self.assertEqual(recovery['destination'], str(self.destination))
        self.assertFalse(recovery['ownership_enabled'])

    def test_recovery_preserves_later_facts_and_retirement_in_the_original_store(self):
        signature = self.snapshot()
        later = self.fixture.remember('Synthetic later live fact survives recovery', 'recovery-later')
        self.fixture.memory.forget(native_fixture.OWNER, self.saved['reference'], 'recovery-later-forget')
        self.recover(signature)
        self.assertEqual(self.fixture.memory.get(native_fixture.OWNER, later['reference'])['content'],
                         'Synthetic later live fact survives recovery')
        self.assertEqual(self.fixture.memory.get(native_fixture.OWNER, self.saved['reference'])['status'], 'conflict')
        recalled = self.fixture.memory.recall(native_fixture.OWNER, 'complete native recovery fact')
        self.assertNotIn('Synthetic complete native recovery fact', [item['content'] for item in recalled])

    def test_recovery_works_after_the_live_user_data_boundary_is_unavailable(self):
        signature = self.snapshot()
        user = self.fixture.home / '.config/LIFEOS/USER'
        retained = user.with_name('retained-user-data')
        user.rename(retained)
        result = self.recover(signature)
        recovered = NativeMemory(Path(result['root']))
        self.assertEqual(recovered.get(native_fixture.OWNER, self.saved['reference'])['content'],
                         'Synthetic complete native recovery fact')
        self.assertTrue(retained.is_dir())
        self.assertFalse(user.exists())

    def test_recovery_refuses_existing_targets_and_preserves_their_contents(self):
        signature = self.snapshot()
        self.destination.mkdir(parents=True)
        marker = self.destination / 'existing-owner-data'
        marker.write_text('Preserve this recovery target.\n')
        with self.assertRaises(MemoryUnavailable):
            self.recover(signature)
        self.assertEqual(marker.read_text(), 'Preserve this recovery target.\n')

    def test_recovery_requires_owner_authority_and_the_reviewed_signature(self):
        signature = self.snapshot()
        with self.assertRaises(MemoryUnavailable):
            recover(self.fixture.memory, native_fixture.READER, self.backup, signature, self.destination)
        with self.assertRaises(MemoryUnavailable):
            self.recover('0' * 64)
        self.assertFalse(self.destination.exists())

    def test_recovery_refuses_a_target_inside_live_data_or_the_backup(self):
        signature = self.snapshot()
        for destination in (self.fixture.root / 'recovery', self.fixture.home / '.config/LIFEOS/USER/recovery',
                            self.backup / 'recovery'):
            with self.subTest(destination=destination), self.assertRaises(MemoryUnavailable):
                recover(self.fixture.memory, native_fixture.OWNER, self.backup, signature, destination)
            self.assertFalse(destination.exists())

    def test_recovery_refuses_a_redirected_destination_parent(self):
        signature = self.snapshot()
        actual = self.fixture.home / 'actual-recovery'
        actual.mkdir()
        self.destination.parent.symlink_to(actual)
        with self.assertRaises(MemoryUnavailable):
            self.recover(signature)
        self.assertEqual(list(actual.iterdir()), [])

    def test_process_exit_before_publication_preserves_live_data_and_a_private_recovery_tree(self):
        signature = self.snapshot()
        script = '''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
import lifeos_hook_bridge.memory_backup_recovery as recovery
from test_memory_native import OWNER
settings=json.loads(sys.stdin.read())
def stop_before_publication(source,destination):
    os._exit(73)
recovery.os.rename=stop_before_publication
recovery.recover(NativeMemory(Path(settings['root'])),OWNER,Path(settings['backup']),settings['signature'],Path(settings['destination']))
'''
        result = subprocess.run([sys.executable, '-W', 'error::ResourceWarning', '-c', script],
            input=json.dumps({'root': str(self.fixture.root), 'backup': str(self.backup),
                'signature': signature, 'destination': str(self.destination)}),
            env=os.environ.copy(), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertFalse(self.destination.exists())
        leftovers = list(self.destination.parent.glob('.recovery-*'))
        self.assertEqual(len(leftovers), 1)
        candidate = leftovers[0]
        self.assertEqual(candidate.stat().st_mode & 0o777, 0o700)
        metadata = json.loads((candidate / '.native-recovery.json').read_text())
        self.assertEqual(metadata['signature'], signature)
        self.assertFalse(metadata['ownership_enabled'])
        recovered = NativeMemory(candidate / '.claude')
        self.assertEqual(recovered.get(native_fixture.OWNER, self.saved['reference'])['content'],
                         'Synthetic complete native recovery fact')
        self.assertEqual(self.fixture.memory.get(native_fixture.OWNER, self.saved['reference'])['content'],
                         'Synthetic complete native recovery fact')
        self.assertEqual(self.recover(signature)['status'], 'recovered')
        self.assertTrue(candidate.is_dir())
