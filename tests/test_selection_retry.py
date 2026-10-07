# ABOUTME: Checks native mount compensation retries after real recovery process exits.
# ABOUTME: Preserves later owner edits across target checkpoints and previous mount commits.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_selection_native_mount as native_fixture
from lifeos_hook_bridge.installation_selection import recover_selection
from lifeos_hook_bridge.selection_worker import _mount, _recover_mount


CHILD = '''
import os, sys
from pathlib import Path
from lifeos_hook_bridge import installation_selection as selection
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.selection_worker import _mount, _recover_mount
profile, target, job = map(Path, sys.argv[1:4])
hermes, phase = sys.argv[4:]
native = _mount(profile, {'hermes_command': hermes})
class Services:
    def stop(self): pass
    def start(self): pass
    def point_pulse(self, home): pass
def mount(installed, baseline):
    native(installed, baseline)
    if phase in {'select', 'previous-committed'}: os._exit(91)
if phase == 'checkpoint':
    record = selection._record
    def interrupted(job, journal, state):
        record(job, journal, state)
        if journal.get('target_mount_recovered'): os._exit(92)
    selection._record = interrupted
if phase == 'previous-selected':
    clear = selection.clear
    def interrupted_clear(profile):
        clear(profile)
        os._exit(93)
    selection.clear = interrupted_clear
arguments = dict(configuration=MemoryConfiguration(profile / 'lifeos-memory.json'),
    services=Services(), mount=mount, recover_mount=lambda installed, previous: _recover_mount(installed, profile, previous=previous),
    verify=lambda: None)
if phase == 'select':
    selection.select_home(job, profile=profile, target=target, baseline_data=None, **arguments)
else:
    selection.recover_selection(job, **arguments)
'''


class SelectionRetryTests(unittest.TestCase):
    def setUp(self):
        fixture = native_fixture.SelectionNativeMountTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        fixture.fixture.configuration.update(lambda config: config.update(ownership_enabled=False))
        (fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.target = fixture.root.parent / 'selection-target/home/.claude'
        shutil.copytree(fixture.root, self.target)
        (self.target / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md').write_text('# SyntheticTargetConstitution\n')
        environment = {key: value for key, value in fixture.environment.items()
                       if key != 'LIFEOS_MEMORY_ADMINISTRATION'}
        active = patch.dict(os.environ, environment, clear=True)
        active.start()
        self.addCleanup(active.stop)
        self.mount = _mount(fixture.profile, {'hermes_command': str(fixture.hermes)})
        self.mount(fixture.root, None)
        self.previous_soul = (fixture.profile / 'SOUL.md').read_bytes()
        self.job = fixture.profile / 'selection-retry'
        self.events = []

    def crash(self, phase):
        fixture = self.fixture
        result = subprocess.run([sys.executable, '-c', CHILD, str(fixture.profile), str(self.target.parent),
            str(self.job), str(fixture.hermes), phase], text=True, capture_output=True, timeout=120)
        expected = {'checkpoint': 92, 'previous-selected': 93}.get(phase, 91)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')

    def recover(self):
        events = self.events

        class Services:
            def stop(self): events.append('stop')
            def start(self): events.append('start')
            def point_pulse(self, home): events.append('pulse')

        return recover_selection(self.job, configuration=self.fixture.fixture.configuration,
            services=Services(), mount=self.mount,
            recover_mount=lambda installed, previous: _recover_mount(installed, self.fixture.profile, previous=previous),
            verify=lambda: events.append('verify'))

    def test_owner_edit_after_target_recovery_checkpoint_blocks_retry(self):
        self.assert_edit_preserved('checkpoint')

    def test_owner_edit_after_previous_native_commit_blocks_retry(self):
        self.assert_edit_preserved('previous-committed')

    def test_owner_edit_after_previous_setting_restore_blocks_retry(self):
        self.assert_edit_preserved('previous-selected')

    def assert_edit_preserved(self, phase):
        self.crash('select')
        self.crash(phase)
        self.assertTrue(json.loads((self.job / 'journal.json').read_text())['target_mount_recovered'])
        soul = self.fixture.profile / 'SOUL.md'
        soul.write_text('# SyntheticOwnerEditAfterRecoveryExit\n')
        for attempt in range(2):
            with self.subTest(attempt=attempt), self.assertRaisesRegex(RuntimeError, 'later edit'):
                self.recover()
            self.assertEqual(soul.read_text(), '# SyntheticOwnerEditAfterRecoveryExit\n')
            self.assertNotIn('start', self.events)
            self.assertNotIn('verify', self.events)
            self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolling_back')

    def test_target_checkpoint_without_later_edits_can_resume(self):
        self.crash('select')
        self.crash('checkpoint')
        self.assertEqual(self.recover()['state'], 'rolled_back')
        self.assertEqual((self.fixture.profile / 'SOUL.md').read_bytes(), self.previous_soul)

    def test_previous_commit_without_later_edits_can_resume(self):
        self.crash('select')
        self.crash('previous-committed')
        self.assertEqual(self.recover()['state'], 'rolled_back')
        self.assertEqual((self.fixture.profile / 'SOUL.md').read_bytes(), self.previous_soul)

    def test_previous_setting_restore_without_later_edits_can_resume(self):
        self.crash('select')
        self.crash('previous-selected')
        self.assertEqual(self.recover()['state'], 'rolled_back')
        self.assertEqual((self.fixture.profile / 'SOUL.md').read_bytes(), self.previous_soul)
