# ABOUTME: Exercises server-owned SSH memory enrollment and revocation.
# ABOUTME: Uses synthetic credentials and private files without changing host SSH configuration.
import base64
import concurrent.futures
from pathlib import Path
import struct
import unittest
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_sharing import MemorySharing
import test_memory_service as service_fixture


def public_key(value: int) -> str:
    algorithm = b'ssh-ed25519'
    raw = struct.pack('>I',len(algorithm))+algorithm+struct.pack('>I',32)+bytes([value])*32
    return 'ssh-ed25519 '+base64.b64encode(raw).decode()

class MemorySharingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = service_fixture.MemoryServiceTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.keys = self.fixture.fixture.home / '.ssh/authorized_keys'
        self.keys.parent.mkdir(mode=0o700)
        self.keys.write_text('# Existing unrelated account key\n')
        self.keys.chmod(0o600)
        self.sharing = MemorySharing(self.fixture.config, self.keys, Path('/usr/bin/python3'),
                                     Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py')
    def test_new_key_binds_fixed_client_and_starts_project_read_only(self):
        result = self.sharing.enroll('newresearch',public_key(1)+'\n',projects=['lab'],model_route='unknown')
        self.assertEqual(result['status'],'enrolled')
        grant = MemoryConfiguration(self.fixture.config).load()['clients']['newresearch']
        self.assertEqual(grant['read'],['project']); self.assertEqual(grant['write'],[])
        text = self.keys.read_text()
        self.assertTrue(text.startswith('# Existing unrelated account key\n'))
        self.assertIn('restrict,command=',text)
        self.assertIn('--client newresearch',text); self.assertIn('--ssh',text)
        self.assertIn(' -I ',text); self.assertIn('/usr/bin/env -i',text)
        self.assertIn('SSH_ORIGINAL_COMMAND=',text)
        self.assertEqual(self.keys.stat().st_mode & 0o777,0o600)
    def test_revoke_denies_an_open_service_and_preserves_other_keys(self):
        self.sharing.enroll('fresh',public_key(2),projects=['lab'],model_route='unknown',write_project=True)
        self.fixture.fixture.remember()
        self.assertEqual(self.fixture.service.call_client('fresh','lifeos_memory_search',{'query':'synthetic lab'})['status'],'ok')
        self.sharing.revoke('fresh')
        self.assertEqual(self.fixture.service.call_client('fresh','lifeos_memory_search',{'query':'synthetic lab'})['status'],'rejected')
        self.assertNotIn(public_key(2),self.keys.read_text())
        self.assertIn('# Existing unrelated account key',self.keys.read_text())
        with self.assertRaises(ValueError):
            self.sharing.enroll('fresh',public_key(3),projects=['lab'],model_route='unknown')
    def test_id_key_permissions_and_command_injection_are_rejected(self):
        for identifier,key in [('bad;name',public_key(4)),('valid','command="sh" '+public_key(4)),('valid',public_key(4)+'\n'+public_key(5)),('valid','ssh-ed25519 AAAA')]:
            with self.subTest(identifier=identifier,key=key), self.assertRaises(ValueError):
                self.sharing.enroll(identifier,key,projects=['lab'],model_route='unknown')
        self.assertEqual(self.keys.read_text(),'# Existing unrelated account key\n')
        self.sharing.enroll('first',public_key(4),projects=['lab'],model_route='unknown')
        with self.assertRaises(ValueError):
            self.sharing.enroll('second',public_key(4),projects=['lab'],model_route='unknown')
    def test_concurrent_enrollment_preserves_both_grants_and_keys(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda i:self.sharing.enroll(f'agent{i}',public_key(i),projects=['lab'],model_route='unknown'),[5,6]))
        self.assertEqual([r['status'] for r in results],['enrolled','enrolled'])
        grants = MemoryConfiguration(self.fixture.config).load()['clients']
        self.assertIn('agent5',grants); self.assertIn('agent6',grants)
        self.assertIn(public_key(5),self.keys.read_text()); self.assertIn(public_key(6),self.keys.read_text())
    def test_keys_file_symlink_does_not_receive_an_enrollment(self):
        target = self.keys.parent/'other'; target.write_text('unchanged')
        self.keys.unlink(); self.keys.symlink_to(target)
        with self.assertRaises(ValueError):
            self.sharing.enroll('agent',public_key(9),projects=['lab'],model_route='unknown')
        self.assertEqual(target.read_text(),'unchanged')
