# ABOUTME: Measures pending core-edit recovery while a program transaction holds its real locks.
# ABOUTME: Uses an actual process interruption and another authenticated memory route with synthetic config bytes.
import json
from pathlib import Path
import unittest
import httpx
from test_memory_core_editor import MemoryCoreEditorTests
from lifeos_hook_bridge.installation_lock import installation_lock
from lifeos_hook_bridge.program_lock import exclusive


class RecoveryLockProbe(MemoryCoreEditorTests):
    def runTest(self):
        profile = self.fixture.configuration.path.parent
        (self.fixture.home / '.hermes').symlink_to(profile, target_is_directory=True)
        path = profile / 'config.yaml'
        path.write_text('model: synthetic-original\n')
        with httpx.Client(timeout=60) as client:
            self.login(client)
            self.interrupt_save('config', path, client)
            before = path.read_text()
            with installation_lock(profile), exclusive(profile, timeout=0):
                response = client.post(self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/review', json={
                    'tool': 'lifeos_memory_search', 'arguments': {'query': 'authenticated PULSE'}})
                result = {'status': response.status_code, 'response': response.json(), 'before': before,
                    'after_while_program_locks_held': path.read_text()}
        Path(__file__).with_name('recovery-lock-probe.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([RecoveryLockProbe()]))
    raise SystemExit(not outcome.wasSuccessful())
