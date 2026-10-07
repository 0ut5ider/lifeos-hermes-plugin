# ABOUTME: Tests the journaled transaction that selects a LifeOS home for one Hermes profile.
# ABOUTME: Uses real setting and configuration files with recorded service and mount callbacks.
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge import installation_selection as selection_module
from lifeos_hook_bridge import lifeos_installation
from lifeos_hook_bridge.installation_selection import SelectionError, recover_selection, select_home
from lifeos_hook_bridge.memory_service import MemoryConfiguration


class Services:
    def __init__(self, events, *, fail_start=0):
        self.events, self.fail_start = events, fail_start

    def stop(self):
        self.events.append('stop')

    def start(self):
        self.events.append('start')
        if self.fail_start:
            self.fail_start -= 1
            raise RuntimeError('synthetic start failure')

    def point_pulse(self, home):
        self.events.append(('pulse', None if home is None else str(home)))


class InstallationSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.account = self.root / 'account'
        self.profile = self.account / '.hermes'
        self.profile.mkdir(parents=True, mode=0o700)
        self.store = self.root / 'store/home'
        for home in (self.account, self.store):
            (home / '.claude/LIFEOS').mkdir(parents=True)
        environment = patch.dict(os.environ, {'HOME': str(self.account)})
        environment.start()
        self.addCleanup(environment.stop)
        self.configuration = MemoryConfiguration(self.profile / 'lifeos-memory.json')
        self.configuration.save({'version': 1, 'root': str(self.account / '.claude'), 'principal': 'owner',
            'ownership_enabled': False, 'sharing_enabled': False, 'accounts': {'dashboard:basic:owner': 'owner'},
            'destinations': {}, 'clients': {}})
        self.events = []
        self.job = self.profile / '.lifeos-installation/selection/job-1'

    def mount(self, installed, baseline_data):
        self.events.append(('mount', str(installed), baseline_data))
        if getattr(self, 'fail_mount', None) == installed:
            raise RuntimeError('synthetic mount failure')

    def select(self, target, services=None, verify=lambda: None):
        return select_home(self.job, profile=self.profile, target=target, configuration=self.configuration,
                           services=services or Services(self.events), mount=self.mount, recover_mount=lambda installed, previous: None, verify=verify,
                           baseline_data=b'synthetic baseline' if target is not None else None)

    def test_selects_a_store_and_returns_to_the_account_home(self):
        result = self.select(self.store)
        self.assertEqual(result['state'], 'applied')
        selected = lifeos_installation.selection(self.profile)
        self.assertEqual(selected.home, self.store)
        self.assertEqual(selected.workspace, self.account / 'HermesWorkspace')
        self.assertEqual(self.configuration.load()['root'], str(self.store / '.claude'))
        self.assertEqual(self.events, ['stop', ('pulse', str(self.store)),
            ('mount', str(self.store / '.claude'), b'synthetic baseline'), 'start'])
        self.events.clear()
        self.job = self.profile / '.lifeos-installation/selection/job-2'
        returned = self.select(None)
        self.assertEqual(returned['state'], 'applied')
        self.assertFalse((self.profile / lifeos_installation.SETTING).exists())
        self.assertEqual(self.configuration.load()['root'], str(self.account / '.claude'))
        self.assertEqual(self.events, ['stop', ('pulse', None),
            ('mount', str(self.account / '.claude'), None), 'start'])

    def test_mount_failure_restores_the_previous_selection(self):
        self.fail_mount = self.store / '.claude'
        with self.assertRaisesRegex(SelectionError, 'synthetic mount failure'):
            self.select(self.store)
        self.assertFalse((self.profile / lifeos_installation.SETTING).exists())
        self.assertEqual(self.configuration.load()['root'], str(self.account / '.claude'))
        self.assertEqual(self.events, ['stop', ('pulse', str(self.store)),
            ('mount', str(self.store / '.claude'), b'synthetic baseline'), 'stop', ('pulse', None),
            ('mount', str(self.account / '.claude'), None), 'start'])
        self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolled_back')

    def test_failed_start_remounts_the_previous_installation(self):
        with self.assertRaisesRegex(SelectionError, 'synthetic start failure'):
            self.select(self.store, services=Services(self.events, fail_start=1))
        self.assertFalse((self.profile / lifeos_installation.SETTING).exists())
        self.assertIn(('mount', str(self.account / '.claude'), None), self.events)
        self.assertEqual(self.events[-1], 'start')
        self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolled_back')

    def test_recovery_after_process_death_restores_the_previous_selection(self):
        for step in ('stopped', 'published', 'mounting', 'mounted'):
            with self.subTest(step=step):
                self.events.clear()
                original = selection_module._record

                def interrupted(job, journal, state):
                    original(job, journal, state)
                    if state == step:
                        raise KeyboardInterrupt(step)

                with patch.object(selection_module, '_record', interrupted), self.assertRaises(KeyboardInterrupt):
                    self.select(self.store)
                result = recover_selection(self.job, configuration=self.configuration,
                                           services=Services(self.events), mount=self.mount, recover_mount=lambda installed, previous: None, verify=lambda: None)
                self.assertEqual(result['state'], 'rolled_back')
                self.assertFalse((self.profile / lifeos_installation.SETTING).exists())
                self.assertEqual(self.configuration.load()['root'], str(self.account / '.claude'))
                remounted = ('mount', str(self.account / '.claude'), None) in self.events
                self.assertEqual(remounted, step != 'stopped')
                self.job = self.job.with_name(self.job.name + '-next')

    def test_refuses_a_target_without_an_installed_lifeos(self):
        with self.assertRaisesRegex(SelectionError, 'no installed LifeOS'):
            self.select(self.root / 'empty')
        self.assertEqual(self.events, [])

    def test_death_after_mount_publication_restores_the_previous_mounted_files(self):
        soul = self.profile / 'SOUL.md'
        soul.write_text(str(self.account / '.claude'))
        program = '''
import os, sys
from pathlib import Path
from lifeos_hook_bridge.installation_selection import select_home
from lifeos_hook_bridge.memory_service import MemoryConfiguration
class Services:
    def stop(self): pass
    def start(self): pass
    def point_pulse(self, home): pass
profile, target, job = map(Path, sys.argv[1:])
def mount(installed, baseline):
    (profile / 'SOUL.md').write_text(str(installed))
    os._exit(91)
select_home(job, profile=profile, target=target,
    configuration=MemoryConfiguration(profile / 'lifeos-memory.json'),
    services=Services(), mount=mount, recover_mount=lambda installed, previous: None, verify=lambda: None, baseline_data=None)
'''
        result = subprocess.run([sys.executable, '-c', program, str(self.profile), str(self.store), str(self.job)],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(soul.read_text(), str(self.store / '.claude'))

        def mount(installed, baseline):
            soul.write_text(str(installed))

        recovered = recover_selection(self.job, configuration=self.configuration,
                                      services=Services(self.events), mount=mount, recover_mount=lambda installed, previous: None, verify=lambda: None)
        self.assertEqual(recovered['state'], 'rolled_back')
        self.assertEqual(soul.read_text(), str(self.account / '.claude'))
        self.assertEqual(self.configuration.load()['root'], soul.read_text())
        self.assertEqual(str(lifeos_installation.selection(self.profile).installed), soul.read_text())

    def test_mount_exception_after_publication_restores_the_previous_mounted_files(self):
        soul = self.profile / 'SOUL.md'

        def mount(installed, baseline):
            soul.write_text(str(installed))
            if installed == self.store / '.claude':
                raise RuntimeError('synthetic failure after publication')

        with self.assertRaisesRegex(SelectionError, 'failure after publication'):
            select_home(self.job, profile=self.profile, target=self.store, configuration=self.configuration,
                        services=Services(self.events), mount=mount, recover_mount=lambda installed, previous: None, verify=lambda: None, baseline_data=None)
        self.assertEqual(soul.read_text(), str(self.account / '.claude'))

    def test_changed_memory_root_prevents_starting_the_target_services(self):
        def mount(installed, baseline):
            if installed == self.store / '.claude':
                self.configuration.update(lambda value: value.update(root=str(self.account / '.claude')))

        with self.assertRaisesRegex(SelectionError, 'configuration disagree'):
            select_home(self.job, profile=self.profile, target=self.store, configuration=self.configuration,
                services=Services(self.events), mount=mount, recover_mount=lambda installed, previous: None,
                verify=lambda: None, baseline_data=None)
        self.assertEqual(self.events.count('start'), 1, 'Only the restored installation can start')
        self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolled_back')

    def test_changed_selection_prevents_starting_the_target_services(self):
        def mount(installed, baseline):
            if installed == self.store / '.claude':
                lifeos_installation.clear(self.profile)

        with self.assertRaisesRegex(SelectionError, 'configuration disagree'):
            select_home(self.job, profile=self.profile, target=self.store, configuration=self.configuration,
                services=Services(self.events), mount=mount, recover_mount=lambda installed, previous: None,
                verify=lambda: None, baseline_data=None)
        self.assertEqual(self.events.count('start'), 1)
        self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolled_back')

    def crash_native_mount(self, phase):
        program = '''
import hashlib, os, sys
from pathlib import Path
from uuid import uuid4
from lifeos_hook_bridge import mount_transaction as native
from lifeos_hook_bridge.installation_selection import select_home, recover_selection
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.selection_worker import _recover_mount
from lifeos_hook_bridge.version_drift import default_baseline_path
profile, target, job = map(Path, sys.argv[1:4])
phase = sys.argv[4]
configuration = MemoryConfiguration(profile / 'lifeos-memory.json')
class Services:
    def stop(self): pass
    def start(self): pass
    def point_pulse(self, home): pass
def mount(installed, baseline):
    transaction = native.MountTransaction(installed, profile, default_baseline_path(installed.parent))
    with transaction._lock():
        snapshot = transaction.state / uuid4().hex
        snapshot.mkdir(mode=0o700)
        (snapshot / 'previous').mkdir()
        (snapshot / 'selected').mkdir()
        native._json(snapshot / 'identity.json', transaction._snapshot_identity())
        soul = profile / 'SOUL.md'
        before_data, before = native._read(soul)
        selected = str(installed).encode()
        native.publish(snapshot / 'previous/0', before_data)
        native.publish(snapshot / 'selected/0', selected)
        manifest = {'version': 1, 'profile': str(profile), 'installed': str(installed),
            'baseline': str(transaction.baseline), 'snapshot': str(snapshot), 'state': 'prepared',
            'workspace': str(Path(os.environ['HOME']) / 'HermesWorkspace'), 'absent_directories': [],
            'entries': [{'target': str(soul), 'before': before,
                'after': {'digest': hashlib.sha256(selected).hexdigest(), 'mode': 0o600}, 'copy': 0}]}
        native._json(transaction.journal, manifest)
        transaction._publish(manifest)
        if phase == 'select-committed':
            manifest['state'] = 'committed'
            native._json(transaction.journal, manifest)
        os._exit(93 if phase == 'recover-previous' else 91)
recover_mount = lambda installed, previous: _recover_mount(installed, profile, previous=previous)
if phase.startswith('select-'):
    select_home(job, profile=profile, target=target, configuration=configuration, services=Services(),
        mount=mount, recover_mount=recover_mount, verify=lambda: None, baseline_data=None)
else:
    if phase == 'recover-target':
        publish = native.publish
        def interrupted(path, data):
            publish(path, data)
            if path == profile / 'SOUL.md': os._exit(92)
        native.publish = interrupted
    recover_selection(job, configuration=configuration, services=Services(), mount=mount,
        recover_mount=recover_mount, verify=lambda: None)
'''
        result = subprocess.run([sys.executable, '-c', program, str(self.profile), str(self.store),
                                 str(self.job), phase], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, {'recover-target': 92, 'recover-previous': 93}.get(phase, 91),
                         result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')

    def recover_native_mount(self):
        from lifeos_hook_bridge.selection_worker import _recover_mount

        def mount(installed, baseline):
            _recover_mount(installed, self.profile)
            self.events.append(('mount', str(installed)))
            (self.profile / 'SOUL.md').write_text(str(installed))

        return recover_selection(self.job, configuration=self.configuration, services=Services(self.events),
            mount=mount, recover_mount=lambda installed, previous: _recover_mount(installed, self.profile, previous=previous),
            verify=lambda: None)

    def prepare_previous_mount(self):
        soul = self.profile / 'SOUL.md'
        soul.write_text(str(self.account / '.claude'))
        soul.chmod(0o600)

    def test_recovers_pending_target_mount_before_restoring_the_selection(self):
        self.prepare_previous_mount()
        self.crash_native_mount('select-applying')
        self.assertEqual(self.recover_native_mount()['state'], 'rolled_back')
        self.assertEqual((self.profile / 'SOUL.md').read_text(), str(self.account / '.claude'))
        self.assertEqual(self.configuration.load()['root'], str(self.account / '.claude'))

    def test_recovers_completed_target_mount_before_the_outer_mount_stamp(self):
        self.prepare_previous_mount()
        self.crash_native_mount('select-committed')
        self.assertEqual(self.recover_native_mount()['state'], 'rolled_back')
        self.assertEqual((self.profile / 'SOUL.md').read_text(), str(self.account / '.claude'))

    def test_process_death_during_target_mount_recovery_can_resume(self):
        self.prepare_previous_mount()
        self.crash_native_mount('select-applying')
        self.crash_native_mount('recover-target')
        journal = json.loads((self.job / 'journal.json').read_text())
        self.assertEqual(journal['state'], 'rolling_back')
        self.assertFalse(journal.get('target_mount_recovered', False))
        self.assertEqual(self.recover_native_mount()['state'], 'rolled_back')
        self.assertEqual((self.profile / 'SOUL.md').read_text(), str(self.account / '.claude'))

    def test_process_death_during_previous_mount_does_not_recover_the_wrong_target(self):
        self.prepare_previous_mount()
        self.crash_native_mount('select-applying')
        self.crash_native_mount('recover-previous')
        self.assertTrue(json.loads((self.job / 'journal.json').read_text())['target_mount_recovered'])
        self.assertEqual(self.recover_native_mount()['state'], 'rolled_back')
        self.assertEqual((self.profile / 'SOUL.md').read_text(), str(self.account / '.claude'))

    def test_later_edit_blocks_rollback_before_selection_restore_or_service_restart(self):
        self.prepare_previous_mount()
        self.crash_native_mount('select-applying')
        (self.profile / 'SOUL.md').write_text('SyntheticLaterOwnerEdit')
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            self.recover_native_mount()
        self.assertEqual((self.profile / 'SOUL.md').read_text(), 'SyntheticLaterOwnerEdit')
        self.assertEqual(lifeos_installation.selection(self.profile).home, self.store)
        self.assertNotIn('start', self.events)
        self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolling_back')


if __name__ == '__main__':
    unittest.main()
