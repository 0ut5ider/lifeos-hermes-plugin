# ABOUTME: Verifies store-selection rollback through real native mounting and Hermes config checks.
# ABOUTME: Kills actual processes during publication and before the outer mount completion stamp.
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_mount_transaction as mount_fixture


class SelectionNativeMountTests(unittest.TestCase):
    def setUp(self):
        fixture = mount_fixture.MountTransactionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture.fixture
        self.root, self.profile, self.hermes = fixture.root, fixture.profile, fixture.hermes
        self.environment = fixture.environment

    def test_selection_recovery_remounts_the_previous_native_installation_after_process_death(self):
        from lifeos_hook_bridge.installation_selection import recover_selection
        from lifeos_hook_bridge.lifeos_installation import selection
        from lifeos_hook_bridge.selection_worker import _mount, _recover_mount
        self.fixture.configuration.update(lambda config: config.update(ownership_enabled=False))
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        target = self.root.parent / 'selection-target/home/.claude'
        shutil.copytree(self.root, target)
        (target / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md').write_text('# SyntheticTargetConstitution\n')
        environment = {key: value for key, value in self.environment.items()
                       if key != 'LIFEOS_MEMORY_ADMINISTRATION'}
        request = {'hermes_command': str(self.hermes)}
        mount = _mount(self.profile, request)
        program = '''
import os, sys
from pathlib import Path
from lifeos_hook_bridge import mount_transaction as native
from lifeos_hook_bridge.installation_selection import select_home
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.selection_worker import _mount, _recover_mount
profile, target, job = map(Path, sys.argv[1:4])
hermes, phase = sys.argv[4:]
class Services:
    def stop(self): pass
    def start(self): pass
    def point_pulse(self, home): pass
if phase == 'applying':
    publish = native.publish
    def interrupted(path, data):
        publish(path, data)
        if path == profile / 'SOUL.md': os._exit(91)
    native.publish = interrupted
native_mount = _mount(profile, {'hermes_command': hermes})
def mount(installed, baseline):
    native_mount(installed, baseline)
    os._exit(91)
select_home(job, profile=profile, target=target,
    configuration=MemoryConfiguration(profile / 'lifeos-memory.json'), services=Services(),
    mount=mount, recover_mount=lambda installed: _recover_mount(installed, profile),
    verify=lambda: None, baseline_data=None)
'''

        class Services:
            def stop(self): pass
            def start(self): pass
            def point_pulse(self, home): pass

        with patch.dict(os.environ, environment, clear=True):
            for phase in ('applying', 'committed'):
                with self.subTest(phase=phase):
                    mount(self.root, None)
                    previous_soul = (self.profile / 'SOUL.md').read_bytes()
                    job = self.profile / ('selection-' + phase)
                    result = subprocess.run([sys.executable, '-c', program, str(self.profile), str(target.parent),
                        str(job), str(self.hermes), phase], text=True, capture_output=True, timeout=120)
                    self.assertEqual(result.returncode, 91, result.stdout + result.stderr)
                    self.assertEqual(result.stderr, '')
                    self.assertIn('SyntheticTargetConstitution', (self.profile / 'SOUL.md').read_text())
                    recovered = recover_selection(job, configuration=self.fixture.configuration,
                        services=Services(), mount=mount,
                        recover_mount=lambda installed: _recover_mount(installed, self.profile), verify=lambda: None)
                    self.assertEqual(recovered['state'], 'rolled_back')
                    self.assertEqual(selection(self.profile).installed, self.root)
                    self.assertEqual(self.fixture.configuration.load()['root'], str(self.root))
                    self.assertEqual((self.profile / 'SOUL.md').read_bytes(), previous_soul)
                    from lifeos_hook_bridge.version_drift import default_baseline_path
                    from lifeos_hook_bridge.mount_transaction import MountTransaction
                    transaction = MountTransaction(self.root, self.profile, default_baseline_path(self.root.parent))
                    self.assertEqual(transaction.status()['state'], 'committed')



if __name__ == '__main__':
    unittest.main()
