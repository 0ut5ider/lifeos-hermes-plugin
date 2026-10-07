# ABOUTME: Tests the journaled transaction that selects a LifeOS home for one Hermes profile.
# ABOUTME: Uses real setting and configuration files with recorded service and mount callbacks.
import json
import os
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
                           services=services or Services(self.events), mount=self.mount, verify=verify,
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
            ('mount', str(self.store / '.claude'), b'synthetic baseline'), 'stop', ('pulse', None), 'start'])
        self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolled_back')

    def test_failed_start_remounts_the_previous_installation(self):
        with self.assertRaisesRegex(SelectionError, 'synthetic start failure'):
            self.select(self.store, services=Services(self.events, fail_start=1))
        self.assertFalse((self.profile / lifeos_installation.SETTING).exists())
        self.assertIn(('mount', str(self.account / '.claude'), None), self.events)
        self.assertEqual(self.events[-1], 'start')
        self.assertEqual(json.loads((self.job / 'journal.json').read_text())['state'], 'rolled_back')

    def test_recovery_after_process_death_restores_the_previous_selection(self):
        for step in ('stopped', 'published', 'mounted'):
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
                                           services=Services(self.events), mount=self.mount, verify=lambda: None)
                self.assertEqual(result['state'], 'rolled_back')
                self.assertFalse((self.profile / lifeos_installation.SETTING).exists())
                self.assertEqual(self.configuration.load()['root'], str(self.account / '.claude'))
                remounted = ('mount', str(self.account / '.claude'), None) in self.events
                self.assertEqual(remounted, step == 'mounted')
                self.job = self.job.with_name(self.job.name + '-next')

    def test_refuses_a_target_without_an_installed_lifeos(self):
        with self.assertRaisesRegex(SelectionError, 'no installed LifeOS'):
            self.select(self.root / 'empty')
        self.assertEqual(self.events, [])


if __name__ == '__main__':
    unittest.main()
