# ABOUTME: Verifies profile service drain and recovery through actual user systemd units.
# ABOUTME: Uses isolated parent and child writers to check durable intent and control group boundaries.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4

from lifeos_hook_bridge.memory_access import MemoryUnavailable


class ProfileServicesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='profile-services-')
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        self.profile = self.home / '.hermes'
        self.installed = self.home / '.claude'
        self.profile.mkdir(mode=0o700)
        (self.installed / 'LIFEOS/PULSE').mkdir(parents=True)
        self.units = {role: f'lifeos-ownership-test-{uuid4().hex}-{role}.service'
            for role in ('gateway', 'dashboard', 'pulse')}
        self.addCleanup(self.stop_units)
        self.directories = {'gateway': self.profile, 'dashboard': self.home,
            'pulse': self.installed / 'LIFEOS/PULSE'}
        unit_directory = self.home / 'units'
        unit_directory.mkdir()
        for role, unit in self.units.items():
            unit_file = unit_directory / unit
            arguments = [sys.executable, str(Path(__file__).with_name('profile_service_writer.py')),
                role, str(self.home / role)]
            unit_file.write_text('# ABOUTME: Runs an isolated ownership service control.\n'
                '# ABOUTME: Contains no production profile or messaging settings.\n'
                '[Unit]\nDescription=LifeOS synthetic ownership control\n[Service]\nType=simple\n'
                'WorkingDirectory=' + str(self.directories[role]) + '\nExecStart=' +
                ' '.join(json.dumps(argument) for argument in arguments) + '\n'
                'KillMode=' + ('mixed' if role == 'gateway' else 'control-group') + '\n'
                'TimeoutStopSec=1s\nRestart=no\n')
            self.command('systemctl', '--user', '--quiet', 'link', '--runtime', str(unit_file))
        self.command('systemctl', '--user', 'daemon-reload')
        for role in self.units:
            self.start_unit(role)

    def command(self, *arguments):
        result = subprocess.run(arguments, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def start_unit(self, role):
        self.command('systemctl', '--user', 'start', self.units[role])
        deadline = time.monotonic() + 5
        while not all((self.home / (role + suffix)).exists() for suffix in ('.ready', '.child-ready')):
            if time.monotonic() > deadline:
                self.fail('The actual service writers do not become ready: ' + role)
            time.sleep(0.02)

    def stop_units(self):
        self.command('systemctl', '--user', 'stop', *self.units.values())
        self.command('systemctl', '--user', '--quiet', 'disable', '--runtime', *self.units.values())
        self.command('systemctl', '--user', 'daemon-reload')

    def barrier(self):
        from lifeos_hook_bridge.profile_services import ProfileServices
        return ProfileServices(self.profile, self.installed, units=self.units)

    def properties(self, role):
        text = self.command('systemctl', '--user', 'show', self.units[role],
            '--property=ActiveState,MainPID,ControlGroup,FragmentPath', '--no-pager')
        return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)

    def record(self, name, data):
        destination = os.environ.get('LIFEOS_SERVICES_EVIDENCE_DIR')
        if destination:
            path = Path(destination)
            path.mkdir(parents=True, exist_ok=True)
            (path / (self._testMethodName + '-' + name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_drain_stops_all_actual_writers_and_resume_restarts_the_selected_units(self):
        before = {role: self.properties(role) for role in self.units}
        self.assertTrue(all(value['ActiveState'] == 'active' for value in before.values()))
        result = self.barrier().drain()
        self.assertEqual(result['state'], 'stopped')
        self.assertEqual(result['services_stopped'], ['gateway', 'pulse', 'dashboard'])
        self.assertFalse(result['owner_turn_verified'])
        stopped = {role: self.properties(role) for role in self.units}
        self.assertTrue(all(value['MainPID'] == '0' for value in stopped.values()), stopped)
        for value in before.values():
            path = Path('/sys/fs/cgroup') / value['ControlGroup'].lstrip('/') / 'cgroup.events'
            self.assertTrue(not path.exists() or 'populated 0' in path.read_text())
        restarted = self.barrier().resume()
        self.assertEqual(restarted['state'], 'active')
        self.assertEqual(restarted['services_started'], ['dashboard', 'pulse', 'gateway'])
        after = {role: self.properties(role) for role in self.units}
        for role in before:
            self.assertEqual(after[role]['ActiveState'], 'active')
            self.assertNotEqual(after[role]['MainPID'], before[role]['MainPID'])
        self.record('lifecycle', {'before': before, 'drain': result, 'stopped': stopped, 'resume': restarted,
            'after': after, 'journal': json.loads(self.barrier().journal.read_text())})

    def test_unit_from_another_profile_refuses_before_any_writer_stops(self):
        before = {role: self.properties(role) for role in self.units}
        other = self.home / 'different-profile'
        other.mkdir(mode=0o700)
        from lifeos_hook_bridge.profile_services import ProfileServices
        with self.assertRaisesRegex(MemoryUnavailable, 'profile|directory'):
            ProfileServices(other, self.installed, units=self.units).drain()
        self.assertEqual({role: self.properties(role)['MainPID'] for role in self.units},
            {role: value['MainPID'] for role, value in before.items()})
        self.record('refusal', {'before': before, 'after': {role: self.properties(role) for role in self.units}})

    def test_process_exit_after_one_stop_retains_original_service_state_for_recovery(self):
        before = {role: self.properties(role) for role in self.units}
        settings = {'profile': str(self.profile), 'installed': str(self.installed), 'units': self.units}
        code = '''import json, os, sys
from pathlib import Path
from lifeos_hook_bridge.profile_services import ProfileServices
settings = json.loads(sys.stdin.read())
def trace(frame, event, argument):
    if event == 'return' and frame.f_code.co_name == '_drain_unit' and frame.f_locals.get('role') == 'gateway':
        os._exit(73)
    return trace
sys.settrace(trace)
ProfileServices(Path(settings['profile']), Path(settings['installed']), units=settings['units']).drain()
'''
        process = subprocess.run([sys.executable, '-c', code], input=json.dumps(settings),
            text=True, capture_output=True, env=os.environ.copy(), timeout=15)
        self.assertEqual(process.returncode, 73, process.stdout + process.stderr)
        self.assertEqual(process.stdout + process.stderr, '')
        self.assertEqual(self.properties('gateway')['MainPID'], '0')
        self.assertEqual(self.properties('pulse')['MainPID'], before['pulse']['MainPID'])
        self.assertTrue(self.barrier().status()['recovery_required'])
        with self.assertRaisesRegex(MemoryUnavailable, 'Recover|recover'):
            self.barrier().drain()
        result = self.barrier().resume()
        self.assertEqual(result['state'], 'active')
        for role in self.units:
            self.assertEqual(self.properties(role)['ActiveState'], 'active')
        self.record('recovery', {'before': before, 'result': result,
            'after': {role: self.properties(role) for role in self.units},
            'journal': json.loads(self.barrier().journal.read_text())})

    def test_recovery_preserves_an_originally_inactive_service(self):
        self.command('systemctl', '--user', 'stop', self.units['pulse'])
        self.barrier().drain()
        self.barrier().verify_stopped()
        result = self.barrier().resume()
        self.assertEqual(result['services_started'], ['dashboard', 'gateway'])
        self.assertEqual(self.properties('pulse')['ActiveState'], 'inactive')
        self.assertEqual(self.properties('pulse')['MainPID'], '0')
        self.record('inactive', {'resume': result, 'after': {role: self.properties(role) for role in self.units}})

    def test_changed_service_definition_refuses_before_any_restart(self):
        self.barrier().drain()
        source = Path(self.properties('pulse')['FragmentPath']).resolve()
        source.write_text(source.read_text() + '# Synthetic later service definition\n')
        self.command('systemctl', '--user', 'daemon-reload')
        with self.assertRaisesRegex(MemoryUnavailable, 'definition'):
            self.barrier().resume()
        for role in self.units:
            self.assertEqual(self.properties(role)['MainPID'], '0')
        self.assertTrue(self.barrier().status()['recovery_required'])
        self.record('changed-definition', {'after': {role: self.properties(role) for role in self.units},
            'journal': json.loads(self.barrier().journal.read_text())})

    def test_definition_change_during_drain_preserves_the_remaining_live_services(self):
        before = {role: self.properties(role) for role in self.units}
        source = Path(before['pulse']['FragmentPath']).resolve()
        original = source.read_bytes()
        changed = False
        def trace(frame, event, argument):
            nonlocal changed
            if not changed and event == 'return' and frame.f_code.co_name == '_drain_unit' and frame.f_locals.get('role') == 'gateway':
                changed = True
                source.write_bytes(original + b'# Synthetic change during drain\n')
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):
                self.barrier().drain()
        finally:
            sys.settrace(None)
        self.assertTrue(changed)
        self.assertEqual(self.properties('gateway')['MainPID'], '0')
        self.assertEqual(self.properties('pulse')['MainPID'], before['pulse']['MainPID'])
        self.assertEqual(self.properties('dashboard')['MainPID'], before['dashboard']['MainPID'])
        self.assertTrue(self.barrier().status()['recovery_required'])
        source.write_bytes(original)
        self.command('systemctl', '--user', 'daemon-reload')
        result = self.barrier().resume()
        self.record('interleaved-definition', {'before': before, 'result': result,
            'after': {role: self.properties(role) for role in self.units}})

    def test_external_service_restart_invalidates_the_stopped_writer_barrier(self):
        self.barrier().drain()
        self.command('systemctl', '--user', 'start', self.units['gateway'])
        with self.assertRaisesRegex(MemoryUnavailable, 'active'):
            self.barrier().verify_stopped()
        self.record('external-start', {'after': {role: self.properties(role) for role in self.units}})

    def test_invalid_service_binding_values_refuse_without_stopping_units(self):
        from lifeos_hook_bridge.profile_services import ProfileServices
        before = {role: self.properties(role)['MainPID'] for role in self.units}
        for value in ([], {}, None, 1, 'hermes-gateway.service --now', 'missing.service'):
            units = {**self.units, 'gateway': value}
            with self.subTest(value=value), self.assertRaises(MemoryUnavailable):
                ProfileServices(self.profile, self.installed, units=units).drain()
        self.assertEqual({role: self.properties(role)['MainPID'] for role in self.units}, before)

    def test_process_exit_after_first_restart_resumes_the_original_service_selection(self):
        self.barrier().drain()
        settings = {'profile': str(self.profile), 'installed': str(self.installed), 'units': self.units}
        code = '''import json, os, sys
from pathlib import Path
from lifeos_hook_bridge.profile_services import ProfileServices
settings = json.loads(sys.stdin.read())
def trace(frame, event, argument):
    if event == 'return' and frame.f_code.co_name == '_run' and frame.f_locals.get('arguments') == ('start', settings['units']['dashboard']):
        os._exit(73)
    return trace
sys.settrace(trace)
ProfileServices(Path(settings['profile']), Path(settings['installed']), units=settings['units']).resume()
'''
        process = subprocess.run([sys.executable, '-c', code], input=json.dumps(settings),
            text=True, capture_output=True, env=os.environ.copy(), timeout=15)
        self.assertEqual(process.returncode, 73, process.stdout + process.stderr)
        self.assertEqual(process.stdout + process.stderr, '')
        interrupted = {role: self.properties(role) for role in self.units}
        self.assertEqual(interrupted['dashboard']['ActiveState'], 'active')
        self.assertEqual(interrupted['gateway']['MainPID'], '0')
        self.assertEqual(interrupted['pulse']['MainPID'], '0')
        self.assertEqual(self.barrier().status()['state'], 'starting')
        result = self.barrier().resume()
        after = {role: self.properties(role) for role in self.units}
        self.assertTrue(all(value['ActiveState'] == 'active' for value in after.values()))
        self.assertEqual(after['dashboard']['MainPID'], interrupted['dashboard']['MainPID'])
        self.record('interrupted-restart', {'interrupted': interrupted, 'result': result, 'after': after,
            'journal': json.loads(self.barrier().journal.read_text())})

    def test_fixed_installed_root_alias_drains_the_same_physical_services(self):
        from lifeos_hook_bridge.profile_services import ProfileServices
        alias = self.home / 'installed-alias'
        alias.symlink_to(self.installed)
        barrier = ProfileServices(self.profile, alias, units=self.units)
        result = barrier.drain()
        self.assertEqual(result['state'], 'stopped')
        self.assertEqual(barrier.resume()['state'], 'active')
        self.record('installed-alias', {'drain': result,
            'journal': json.loads(barrier.journal.read_text())})

    def test_changed_installed_root_alias_refuses_recovery_before_any_restart(self):
        from lifeos_hook_bridge.profile_services import ProfileServices
        alias = self.home / 'installed-alias'
        alias.symlink_to(self.installed)
        barrier = ProfileServices(self.profile, alias, units=self.units)
        barrier.drain()
        other = self.home / 'different-install'
        (other / 'LIFEOS/PULSE').mkdir(parents=True)
        alias.unlink()
        alias.symlink_to(other)
        with self.assertRaises(MemoryUnavailable):
            ProfileServices(self.profile, alias, units=self.units).resume()
        for role in self.units:
            self.assertEqual(self.properties(role)['MainPID'], '0')
        self.record('changed-alias', {'journal': json.loads(barrier.journal.read_text()),
            'after': {role: self.properties(role) for role in self.units}})


if __name__ == '__main__':
    unittest.main()
