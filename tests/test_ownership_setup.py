# ABOUTME: Verifies journaled ownership setup and return with actual native backups and user services.
# ABOUTME: Exercises process interruption and current configuration refusal on synthetic profiles.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from test_memory_ownership import install_connector
import test_memory_native as native_fixture
import test_profile_backup as backup_fixture
import test_profile_services as service_fixture


class OwnershipSetupTests(unittest.TestCase):
    def setUp(self):
        self.backup = backup_fixture.ProfileBackupTests()
        self.backup.setUp()
        self.addCleanup(self.backup.doCleanups)
        self.configuration = self.backup.configuration
        self.configuration.update(lambda value: value.update(ownership_enabled=False,
            accounts={**value['accounts'], 'dashboard:owner': 'owner'}))
        install_connector(self.configuration)
        self.profile = self.backup.profile
        self.original = {name: (self.profile / name).read_bytes()
            for name in ('config.yaml', 'lifeos-memory.json')}
        self.services = service_fixture.ProfileServicesTests()
        self.services.fixture_home = self.backup.fixture.fixture.home
        self.services.fixture_profile = self.profile
        self.services.setUp()
        self.addCleanup(self.services.doCleanups)

    def setup_operation(self):
        from lifeos_hook_bridge.ownership_setup import OwnershipSetup
        return OwnershipSetup(self.configuration, units=self.services.units)

    def prepare(self):
        return self.setup_operation().prepare(self.backup.destination, account='dashboard:owner')

    def pids(self):
        return {role: self.services.properties(role)['MainPID'] for role in self.services.units}

    def record(self, **data):
        directory = os.environ.get('LIFEOS_SETUP_EVIDENCE_DIR')
        if directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            (path / (self._testMethodName + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_reviewed_setup_and_return_preserve_later_facts_and_forgets(self):
        before = self.pids()
        reviewed = self.prepare()
        self.assertEqual(reviewed['state'], 'ready')
        self.assertFalse(reviewed['owner_turn_verified'])
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertTrue(all(pid != '0' for pid in self.pids().values()))
        applied = self.setup_operation().apply(reviewed['signature'], account='dashboard:owner')
        self.assertEqual(applied['state'], 'configured')
        self.assertTrue(self.configuration.load()['ownership_enabled'])
        self.assertFalse(applied['application_verified'])
        self.assertTrue(all(pid != '0' for pid in self.pids().values()))
        saved = self.backup.fixture.fixture.remember('Synthetic fact after complete setup', 'setup-later')
        memory = self.backup.fixture.fixture.memory
        memory.forget(native_fixture.OWNER, self.backup.saved['reference'], 'setup-forget')
        returned = self.setup_operation().recover(account='dashboard:owner')
        self.assertEqual(returned['state'], 'returned')
        for name, content in self.original.items():
            self.assertEqual((self.profile / name).read_bytes(), content)
        self.assertEqual(memory.get(native_fixture.OWNER, saved['reference'])['content'],
            'Synthetic fact after complete setup')
        self.assertEqual(memory.recall(native_fixture.OWNER, 'coherent profile backup'), [])
        self.assertTrue(all(pid != '0' for pid in self.pids().values()))
        self.record(before=before, reviewed=reviewed, applied=applied, returned=returned,
            after=self.pids(), journal=json.loads(self.setup_operation().journal.read_text()))

    def test_changed_review_refuses_before_any_service_stops(self):
        reviewed = self.prepare()
        original_pids = self.pids()
        path = self.profile / 'config.yaml'
        path.write_text(path.read_text() + 'synthetic_later_setting: true\n')
        with self.assertRaises(MemoryUnavailable):
            self.setup_operation().apply(reviewed['signature'], account='dashboard:owner')
        self.assertEqual(self.pids(), original_pids)
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertIn('synthetic_later_setting', path.read_text())
        self.record(reviewed=reviewed, pids=original_pids, journal=json.loads(self.setup_operation().journal.read_text()))

    def test_process_exit_after_first_configuration_write_recovers_before_restart(self):
        reviewed = self.prepare()
        settings = {'configuration': str(self.configuration.path), 'units': self.services.units,
            'signature': reviewed['signature']}
        code = '''import json, os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.ownership_setup import OwnershipSetup
settings = json.loads(sys.stdin.read())
def trace(frame, event, argument):
    if event == 'return' and frame.f_code.co_name == 'publish' and frame.f_locals.get('path') == Path(settings['configuration']).with_name('config.yaml'):
        os._exit(73)
    return trace
sys.settrace(trace)
OwnershipSetup(MemoryConfiguration(Path(settings['configuration'])), units=settings['units']).apply(settings['signature'], account='dashboard:owner')
'''
        child = subprocess.run([sys.executable, '-c', code], input=json.dumps(settings), text=True,
            capture_output=True, env=os.environ.copy(), timeout=30)
        self.assertEqual(child.returncode, 73, child.stdout + child.stderr)
        self.assertEqual(child.stdout + child.stderr, '')
        self.assertEqual(set(self.pids().values()), {'0'})
        self.assertTrue(self.setup_operation().status(account='dashboard:owner')['recovery_required'])
        result = self.setup_operation().recover(account='dashboard:owner')
        self.assertEqual(result['state'], 'returned')
        for name, content in self.original.items():
            self.assertEqual((self.profile / name).read_bytes(), content)
        self.assertTrue(all(pid != '0' for pid in self.pids().values()))
        self.record(reviewed=reviewed, exit=child.returncode, recovery=result,
            journal=json.loads(self.setup_operation().journal.read_text()))

    def interrupted_child(self, action, phase, signature=None):
        settings = {'configuration': str(self.configuration.path), 'units': self.services.units,
            'destination': str(self.backup.destination), 'signature': signature,
            'action': action, 'phase': phase}
        code = '''import json, os, sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.ownership_setup import OwnershipSetup
settings = json.loads(sys.stdin.read())
def trace(frame, event, argument):
    if event != 'return':
        return trace
    name, filename, phase = frame.f_code.co_name, frame.f_code.co_filename, settings['phase']
    stopped = phase == 'first_stop' and name == '_drain_unit' and frame.f_locals.get('role') == 'gateway'
    backup = phase == 'backup' and name == 'create' and filename.endswith('/profile_backup.py')
    committed = phase == 'committed' and name == 'apply' and filename.endswith('/memory_ownership.py')
    restarted = phase == 'restart' and name == '_run' and frame.f_locals.get('arguments') == ('start', settings['units']['dashboard'])
    restore = phase == 'restore' and name == 'publish' and frame.f_locals.get('path') == Path(settings['configuration'])
    drained = phase == 'drained' and name == 'drain' and filename.endswith('/profile_services.py')
    if stopped or backup or committed or restarted or restore or drained:
        os._exit(73)
    return trace
sys.settrace(trace)
operation = OwnershipSetup(MemoryConfiguration(Path(settings['configuration'])), units=settings['units'])
if settings['action'] == 'prepare':
    operation.prepare(Path(settings['destination']), account='dashboard:owner')
elif settings['action'] == 'apply':
    operation.apply(settings['signature'], account='dashboard:owner')
else:
    operation.recover(account='dashboard:owner')
'''
        result = subprocess.run([sys.executable, '-c', code], input=json.dumps(settings), text=True,
            capture_output=True, env=os.environ.copy(), timeout=30)
        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        return result

    def test_interrupted_backup_setup_restart_and_return_restore_the_original_owner(self):
        outcomes = []
        for action, phase in (('prepare', 'first_stop'), ('prepare', 'backup'),
                ('prepare', 'restart'), ('apply', 'committed'), ('apply', 'restart'),
                ('recover', 'restore'), ('recover', 'restart')):
            with self.subTest(action=action, phase=phase):
                case = OwnershipSetupTests()
                case.setUp()
                try:
                    reviewed = case.prepare() if action != 'prepare' else None
                    if action == 'recover':
                        case.setup_operation().apply(reviewed['signature'], account='dashboard:owner')
                    child = case.interrupted_child(action, phase, reviewed['signature'] if reviewed else None)
                    interrupted = case.setup_operation().status(account='dashboard:owner')
                    self.assertTrue(interrupted['recovery_required'])
                    recovered = case.setup_operation().recover(account='dashboard:owner')
                    self.assertEqual(recovered['state'], 'cancelled' if action == 'prepare' else 'returned')
                    for name, content in case.original.items():
                        self.assertEqual((case.profile / name).read_bytes(), content)
                    self.assertTrue(all(pid != '0' for pid in case.pids().values()))
                    outcomes.append({'action': action, 'phase': phase, 'exit': child.returncode,
                        'interrupted': interrupted, 'recovered': recovered, 'pids': case.pids()})
                finally:
                    case.doCleanups()
        self.record(outcomes=outcomes)

    def test_a_second_setup_can_recover_before_replacing_the_previous_return_journal(self):
        first = self.prepare()
        self.setup_operation().apply(first['signature'], account='dashboard:owner')
        self.setup_operation().recover(account='dashboard:owner')
        self.backup.destination = self.backup.destination.with_name('two')
        second = self.prepare()
        self.interrupted_child('apply', 'drained', second['signature'])
        result = self.setup_operation().recover(account='dashboard:owner')
        self.assertEqual(result['state'], 'returned')
        for name, content in self.original.items():
            self.assertEqual((self.profile / name).read_bytes(), content)
        self.assertTrue(all(pid != '0' for pid in self.pids().values()))
        self.record(first=first, second=second, result=result)

    def test_return_preserves_later_configuration_edits_and_keeps_services_drained(self):
        plan = self.prepare()
        self.setup_operation().apply(plan['signature'], account='dashboard:owner')
        path = self.profile / 'config.yaml'
        path.write_text(path.read_text() + 'synthetic_after_setup: preserved\n')
        with self.assertRaisesRegex(MemoryUnavailable, 'later'):
            self.setup_operation().recover(account='dashboard:owner')
        self.assertIn('synthetic_after_setup', path.read_text())
        self.assertEqual(set(self.pids().values()), {'0'})
        self.assertTrue(self.setup_operation().status(account='dashboard:owner')['recovery_required'])
        self.record(pids=self.pids(), journal=json.loads(self.setup_operation().journal.read_text()))

    def test_completed_rollback_with_failed_restart_recovers_after_a_later_edit(self):
        from lifeos_hook_bridge import profile_services
        plan = self.prepare()
        self.setup_operation().apply(plan['signature'], account='dashboard:owner')
        original_resume = profile_services.ProfileServices.resume
        with patch.object(profile_services.ProfileServices, 'resume', side_effect=MemoryUnavailable('synthetic restart failure')):
            with self.assertRaisesRegex(MemoryUnavailable, 'synthetic restart failure'):
                self.setup_operation().recover(account='dashboard:owner')
        self.assertTrue(self.setup_operation().status(account='dashboard:owner')['recovery_required'])
        path = self.profile / 'config.yaml'
        path.write_text(path.read_text() + 'synthetic_after_rollback: preserved\n')
        result = self.setup_operation().recover(account='dashboard:owner')
        self.assertEqual(result['state'], 'returned')
        self.assertIn('synthetic_after_rollback', path.read_text())
        self.assertTrue(all(pid != '0' for pid in self.pids().values()))
        self.assertIs(profile_services.ProfileServices.resume, original_resume)

    def test_originally_inactive_service_stays_inactive_after_setup_and_return(self):
        self.services.command('systemctl', '--user', 'stop', self.services.units['pulse'])
        plan = self.prepare()
        self.setup_operation().apply(plan['signature'], account='dashboard:owner')
        self.assertEqual(self.pids()['pulse'], '0')
        self.setup_operation().recover(account='dashboard:owner')
        self.assertEqual(self.pids()['pulse'], '0')
        self.assertNotEqual(self.pids()['gateway'], '0')
        self.assertNotEqual(self.pids()['dashboard'], '0')

    def test_changed_service_definition_refuses_review_before_any_stop(self):
        plan = self.prepare()
        original = self.pids()
        source = Path(self.services.properties('pulse')['FragmentPath']).resolve()
        source.write_text(source.read_text() + '# Synthetic later unit definition\n')
        self.services.command('systemctl', '--user', 'daemon-reload')
        with self.assertRaisesRegex(MemoryUnavailable, 'review'):
            self.setup_operation().apply(plan['signature'], account='dashboard:owner')
        self.assertEqual(self.pids(), original)

    def test_unqualified_or_other_accounts_cannot_prepare_or_apply_or_recover(self):
        original = self.pids()
        for account in (None, 'owner', 'dashboard:stranger', [], {}):
            with self.subTest(account=account), self.assertRaises(PermissionError):
                self.setup_operation().prepare(self.backup.destination, account=account)
        plan = self.prepare()
        for method in ('apply', 'recover', 'status'):
            with self.subTest(method=method), self.assertRaises(PermissionError):
                arguments = (plan['signature'],) if method == 'apply' else ()
                getattr(self.setup_operation(), method)(*arguments, account='dashboard:stranger')
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertTrue(all(pid != '0' for pid in original.values()))

    def test_changed_journal_metadata_refuses_without_configuration_or_service_effects(self):
        plan = self.prepare()
        journal = self.setup_operation().journal
        document = json.loads(journal.read_text())
        before = self.pids()
        mutations = [('state', []), ('state', {}), ('units', []), ('principal', 'other'),
            ('plan', []), ('plan', None), ('service_signature', 'bad'), ('version', True)]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                journal.write_text(json.dumps({**document, field: value}))
                with self.assertRaises(MemoryUnavailable):
                    self.setup_operation().apply(plan['signature'], account='dashboard:owner')
                self.assertEqual(self.pids(), before)
                self.assertFalse(self.configuration.load()['ownership_enabled'])
        journal.write_text(json.dumps(document))

    def test_external_writer_restart_between_configuration_writes_prevents_native_ownership(self):
        plan = self.prepare()
        changed = False
        def trace(frame, event, argument):
            nonlocal changed
            if (not changed and event == 'return' and frame.f_code.co_name == 'publish'
                    and frame.f_locals.get('path') == self.profile / 'config.yaml'):
                changed = True
                self.services.command('systemctl', '--user', 'start', self.services.units['gateway'])
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaisesRegex(MemoryUnavailable, 'active'):
                self.setup_operation().apply(plan['signature'], account='dashboard:owner')
        finally:
            sys.settrace(None)
        self.assertTrue(changed)
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        result = self.setup_operation().recover(account='dashboard:owner')
        self.assertEqual(result['state'], 'returned')
        for name, content in self.original.items():
            self.assertEqual((self.profile / name).read_bytes(), content)
        self.assertTrue(all(pid != '0' for pid in self.pids().values()))
        self.record(reviewed=plan, changed=changed, result=result)


if __name__ == '__main__':
    unittest.main()
