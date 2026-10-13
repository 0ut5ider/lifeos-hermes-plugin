# ABOUTME: Verifies first-install process discovery against actual synthetic owner processes.
# ABOUTME: Distinguishes Hermes dashboards from unrelated commands with the same argument text.
import os
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from optional.lifeos_release_manager.release_services import check_dashboard_writers, fresh_preview, fresh_services, dashboard_binding, _quoted, _service_paths
from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class ReleaseServiceTests(unittest.TestCase):
    @contextmanager
    def dashboard_boundary(self, *, foreign=False, inactive=False, command='dashboard', bundled=False, extra_source=''):
        from lifeos_hook_bridge.profile_services import _digest
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            profile = home / '.hermes'
            other = home / 'foreign-profile'
            profile.mkdir(mode=0o700)
            other.mkdir(mode=0o700)
            launcher = home / '.local/bin/hermes'
            launcher.parent.mkdir(parents=True)
            ready = home / 'ready'
            launcher.write_text('from pathlib import Path\nimport time\n'
                'Path(' + repr(str(ready)) + ').touch()\ntime.sleep(30)\n')
            launcher.chmod(0o700)
            owner = other if foreign else profile
            process = None
            try:
                if not inactive:
                    arguments = [sys.executable, '-B', str(launcher), 'dashboard']
                    environment = {'HOME': str(home), 'HERMES_HOME': str(owner), 'PATH': os.defpath}
                    if bundled:
                        package = home / 'hermes_cli'
                        package.mkdir()
                        (package / '__init__.py').write_text('')
                        (package / 'main.py').write_text('def main():\n    ' + launcher.read_text().replace('\n', '\n    '))
                        arguments = [sys.executable, '-P', '-c', "import os, site, sys; sys.argv[0]='hermes'; site.addsitedir(os.environ['HERMES_SITE']); from hermes_cli.main import main; sys.exit(main())" + extra_source, 'dashboard']
                        environment.update(PYTHONPATH=str(home), HERMES_SITE=str(home), PYTHONDONTWRITEBYTECODE='1')
                    process = subprocess.Popen(arguments,
                        env=environment,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    deadline = time.monotonic() + 5
                    while not ready.exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(ready.exists())
                group = '' if process is None else Path('/proc/' + str(process.pid) + '/cgroup').read_text().split('0::', 1)[1].strip()
                values = {'ExecStart': '{ path=' + str(launcher) + ' ; argv[]=' + str(launcher) + ' ' + command + ' --isolated --no-open ; }',
                    'FragmentPath': str(home / '.config/systemd/user/hermes-dashboard.service'),
                    'DropInPaths': '', 'ControlGroup': group, 'MainPID': '0' if process is None else str(process.pid)}
                environment = {'HERMES_HOME': str(owner)}
                class ServiceBoundary:
                    def __init__(self, *args, first_installation=False, **kwargs):
                        assert first_installation
                    def preview(self):
                        return {'signature': self._inspect('dashboard')[1]}
                    def _inspect(self, role):
                        return values, 'component-definition'
                def inspect_unit(*args):
                    if '--property=Environment,EnvironmentFiles' in args:
                        return 'Environment=' + ' '.join(key + '=' + value for key, value in environment.items()) + '\nEnvironmentFiles=\n'
                    return 'LoadState=not-found\n'
                module = SimpleNamespace(ProfileServices=ServiceBoundary, _digest=_digest, _run=inspect_unit,
                    UNITS={'dashboard': 'hermes-dashboard.service', 'gateway': 'hermes-gateway.service', 'pulse': 'com.lifeos.pulse.service'})
                current = SimpleNamespace(memory_module=lambda name: module)
                with patch.dict(os.environ, {'HOME': str(home)}):
                    yield current, profile, home / '.claude', values, environment
            finally:
                if process is not None:
                    process.terminate()
                    process.wait(timeout=5)

    def test_official_bundled_dashboard_retains_profile_checks(self):
        for foreign in (False, True):
            with self.subTest(foreign=foreign), self.dashboard_boundary(bundled=True, foreign=foreign) as (current, profile, installed, values, environment):
                if foreign:
                    with self.assertRaisesRegex(ReleaseRejected, 'profile'):
                        fresh_preview(current, profile, installed)
                else:
                    self.assertIn('signature', fresh_preview(current, profile, installed))
                    with self.assertRaisesRegex(ReleaseRejected, 'owner user service'):
                        check_dashboard_writers(profile)

    def test_other_inline_source_does_not_claim_a_bundled_dashboard(self):
        with self.dashboard_boundary(bundled=True, extra_source='; pass') as (current, profile, installed, values, environment):
            with self.assertRaisesRegex(ReleaseRejected, 'command'):
                fresh_preview(current, profile, installed)
            check_dashboard_writers(profile)

    def test_effective_systemd_environment_preserves_literal_percent_path(self):
        from test_profile_services import service_manager_fixture
        with service_manager_fixture(), tempfile.TemporaryDirectory(prefix='release-percent-') as temp:
            home = Path(temp) / 'literal%%name'
            profile = home / '.hermes'
            profile.mkdir(mode=0o700, parents=True)
            _service_paths(home, profile, home / '.claude')
            launcher = home / '.local/bin/hermes'
            launcher.parent.mkdir(parents=True)
            launcher.write_text('#!/bin/sh\nexit 0\n')
            launcher.chmod(0o700)
            unit = 'lifeos-release-percent-' + uuid4().hex + '.service'
            definition = Path(temp) / unit
            definition.write_text('[Unit]\nDescription=Inactive release environment control\n[Service]\n'
                'Environment=' + _quoted('HERMES_HOME=' + str(profile)) + '\n'
                'ExecStart=' + _quoted(launcher, command=True) + ' dashboard --isolated --no-open\n')
            def command(*arguments):
                result = subprocess.run(['systemctl', '--user', *arguments],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stderr, '')
                return result.stdout
            linked = False
            try:
                command('--quiet', 'link', '--runtime', str(definition))
                linked = True
                command('daemon-reload')
                values = dict(line.split('=', 1) for line in command('show', unit,
                    '--property=MainPID,Environment,EnvironmentFiles,ExecStart', '--no-pager').splitlines())
                self.assertEqual(values['MainPID'], '0')
                self.assertEqual(values['Environment'], 'HERMES_HOME=' + str(profile))
                module = SimpleNamespace(UNITS={'dashboard': unit}, _run=command)
                self.assertEqual(dashboard_binding(module, profile, values)['profile'], str(profile))
                definition.write_text(definition.read_text() + 'EnvironmentFile=-/tmp/lifeos-release-nonexistent-environment\n')
                command('daemon-reload')
                with self.assertRaisesRegex(ReleaseRejected, 'profile'):
                    dashboard_binding(module, profile, values)
            finally:
                if linked:
                    command('--quiet', 'disable', '--runtime', unit)
                    command('daemon-reload')

    def test_active_dashboard_from_another_profile_refuses_before_admission(self):
        with self.dashboard_boundary(foreign=True) as (current, profile, installed, values, environment):
            with self.assertRaisesRegex(ReleaseRejected, 'profile'):
                fresh_preview(current, profile, installed)

    def test_inactive_dashboard_from_another_profile_refuses_before_admission(self):
        with self.dashboard_boundary(foreign=True, inactive=True) as (current, profile, installed, values, environment):
            with self.assertRaisesRegex(ReleaseRejected, 'profile'):
                fresh_preview(current, profile, installed)

    def test_dashboard_configuration_requires_a_dashboard_invocation(self):
        with self.dashboard_boundary(command='gateway run') as (current, profile, installed, values, environment):
            with self.assertRaisesRegex(ReleaseRejected, 'dashboard'):
                fresh_preview(current, profile, installed)

    def test_matching_active_and_inactive_dashboard_bindings_remain_available(self):
        for inactive in (False, True):
            with self.subTest(inactive=inactive), self.dashboard_boundary(inactive=inactive) as (current, profile, installed, values, environment):
                self.assertIn('signature', fresh_preview(current, profile, installed))

    def test_first_service_barrier_rechecks_profile_binding_after_preview(self):
        with self.dashboard_boundary(inactive=True) as (current, profile, installed, values, environment):
            services = fresh_services(current, profile, installed)
            services.preview()
            environment['HERMES_HOME'] = str(profile.parent / 'foreign-profile')
            with self.assertRaisesRegex(ReleaseRejected, 'profile'):
                services._inspect('dashboard')

    def test_foreground_detection_uses_the_actual_hermes_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = root / '.hermes'
            profile.mkdir(mode=0o700)
            for name, expected in (('unrelated.py', False), ('hermes', True)):
                with self.subTest(name=name):
                    ready = root / (name + '.ready')
                    script = root / name
                    script.write_text('from pathlib import Path\nimport time\n'
                        'Path(' + repr(str(ready)) + ').touch()\ntime.sleep(30)\n')
                    process = subprocess.Popen([sys.executable, '-B', str(script), 'dashboard'],
                        env=dict(os.environ, HERMES_HOME=str(profile)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try:
                        deadline = time.monotonic() + 5
                        while not ready.exists() and time.monotonic() < deadline:
                            time.sleep(0.01)
                        self.assertTrue(ready.exists())
                        if expected:
                            with self.assertRaisesRegex(ReleaseRejected, 'owner user service'):
                                check_dashboard_writers(profile)
                        else:
                            check_dashboard_writers(profile)
                    finally:
                        process.terminate()
                        process.wait(timeout=5)
