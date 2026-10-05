# ABOUTME: Verifies that SSH enrollment exists only in the separately installed sharing component.
# ABOUTME: Checks the verified loader, the installer, and plugin behavior without the component.
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from lifeos_hook_bridge import memory_preferences
from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_preferences import MemoryPreferences, load_sharing_component
from sharing_component import COMPONENT
import test_memory_sharing as sharing_fixture

PACKAGE = Path(__file__).parents[1] / 'lifeos_hook_bridge'
PROGRAM = PACKAGE / 'memory_mcp.py'


class SharingComponentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = sharing_fixture.MemorySharingTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.fixture
        self.home = self.service.fixture.home
        self.keys = self.fixture.keys

    def preferences(self, component):
        return MemoryPreferences(self.service.config, self.service.fixture.root, Path('/usr/bin/python3'), PROGRAM,
                                 sharing_component=component, sharing_options={'keys_file': self.keys})

    def request(self, value=61):
        return {'client': 'reader', 'public_key': sharing_fixture.public_key(value),
                'projects': ['lab'], 'model_route': 'unknown'}

    def copy(self):
        target = self.home / 'component'
        shutil.copytree(COMPONENT, target)
        os.chmod(target, 0o700)
        return target

    def test_runtime_package_contains_no_ssh_key_file_reference(self):
        pattern = 'authorized' + '_keys'
        hits = [path.relative_to(PACKAGE).as_posix() for path in sorted(PACKAGE.rglob('*'))
                if path.is_file() and '__pycache__' not in path.parts and pattern.encode() in path.read_bytes()]
        self.assertEqual(hits, [])
        self.assertFalse((PACKAGE / 'memory_sharing.py').exists())

    def test_reviewed_component_hash_matches_the_shipped_component(self):
        data = (COMPONENT / 'memory_sharing.py').read_bytes()
        self.assertEqual(memory_preferences.SHARING_COMPONENT_SHA256, hashlib.sha256(data).hexdigest())

    def test_plugin_without_the_component_refuses_enrollment_and_changes_nothing(self):
        preferences = self.preferences(self.home / 'absent-component')
        before = self.keys.read_bytes()
        connections = preferences.status()['connections']
        self.assertFalse(preferences.status()['connection_enrollment_available'])
        with self.assertRaisesRegex(MemoryUnavailable, 'optional sharing component'):
            preferences.enroll(self.request())
        self.assertEqual(self.keys.read_bytes(), before)
        self.assertEqual(preferences.status()['connections'], connections)

    def test_plugin_without_the_component_still_disables_an_enrolled_grant(self):
        installed = self.preferences(COMPONENT)
        self.assertTrue(installed.status()['connection_enrollment_available'])
        installed.enroll(self.request())
        entry = self.keys.read_bytes()
        result = self.preferences(self.home / 'absent-component').revoke('reader')
        self.assertEqual(result, {'status': 'revoked', 'client': 'reader', 'records_deleted': False,
                                  'credential_entry_removed': False})
        self.assertFalse(MemoryConfiguration(self.service.config).load()['clients']['reader']['enabled'])
        self.assertEqual(self.keys.read_bytes(), entry)
        self.assertEqual(installed.revoke('reader')['status'], 'revoked')
        self.assertNotIn(b'lifeos-memory:reader', self.keys.read_bytes())

    def test_loader_refuses_an_altered_linked_or_writable_component(self):
        altered = self.copy()
        with (altered / 'memory_sharing.py').open('a') as stream:
            stream.write('\n# changed after review\n')
        with self.assertRaisesRegex(MemoryUnavailable, 'reviewed'):
            load_sharing_component(altered)
        shutil.rmtree(altered)
        writable = self.copy()
        os.chmod(writable / 'memory_sharing.py', 0o666)
        with self.assertRaisesRegex(MemoryUnavailable, 'owner'):
            load_sharing_component(writable)
        linked = self.home / 'linked-component'
        linked.symlink_to(COMPONENT, target_is_directory=True)
        with self.assertRaisesRegex(MemoryUnavailable, 'owner'):
            load_sharing_component(linked)
        with self.assertRaisesRegex(MemoryUnavailable, 'optional sharing component'):
            load_sharing_component(self.home / 'absent-component')

    def test_installer_publishes_private_files_and_removal_deletes_only_its_files(self):
        profile = self.home / 'profile'
        profile.mkdir(mode=0o700)
        installer = [sys.executable, str(COMPONENT / 'install.py'), '--hermes-home', str(profile)]
        subprocess.run(installer, check=True, capture_output=True, text=True)
        target = profile / 'lifeos-memory-sharing'
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertEqual((target / 'memory_sharing.py').stat().st_mode & 0o777, 0o600)
        self.assertEqual((target / 'memory_sharing.py').read_bytes(), (COMPONENT / 'memory_sharing.py').read_bytes())
        self.assertEqual(self.preferences(target).enroll(self.request())['status'], 'enrolled')
        unrelated = target / 'operator-note.txt'
        unrelated.write_text('keep\n')
        subprocess.run([*installer, '--remove'], check=True, capture_output=True, text=True)
        self.assertFalse((target / 'memory_sharing.py').exists())
        self.assertEqual(unrelated.read_text(), 'keep\n')


@unittest.skipUnless(importlib.util.find_spec('tools') and importlib.util.find_spec('tools.plugin_guard'),
                     'A prepared Hermes source is required')
class InstallScanTests(unittest.TestCase):
    def test_host_scanner_reports_no_critical_finding_and_no_dangerous_verdict(self):
        from tools.plugin_guard import scan_plugin, should_allow_plugin_install
        result = scan_plugin(PACKAGE)
        self.assertEqual([f'{finding.file}:{finding.line}' for finding in result.findings
                          if finding.severity == 'critical'], [])
        self.assertNotEqual(result.verdict, 'dangerous')
        self.assertIsNot(should_allow_plugin_install(result, force=True)[0], False)
