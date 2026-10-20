# ABOUTME: Verifies the owner account boundary separately from native service HOME.
# ABOUTME: Uses actual private directories and child processes to check profile and launcher scope.
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class ReleaseAccountTests(unittest.TestCase):
    def test_installed_inspector_accepts_the_account_launcher_under_native_home(self):
        from lifeos_hook_bridge import lifeos_installation
        from optional.lifeos_release_manager import release_plan
        from optional.lifeos_release_manager.release_programs import ProgramConflict
        from optional.lifeos_release_manager.release_stage import sha, runtime_source_fingerprint
        from test_release_stage import ReleaseStageTests
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary) / 'account'
            profile = owner / '.hermes'
            native_home = owner / 'native/home'
            installed = native_home / '.claude'
            bridge = profile / 'plugins/lifeos-hook-bridge'
            launcher = owner / '.local/bin/hermes'
            for directory in (profile, installed, bridge, launcher.parent):
                directory.mkdir(parents=True, mode=0o700)
            launcher.write_text('#!/bin/sh\nexit 0\n')
            launcher.chmod(0o700)
            lifeos_installation.publish(profile, native_home, owner / 'workspace')
            selection_bytes = (profile / lifeos_installation.SETTING).read_bytes()
            job = profile / '.lifeos-releases' / ('b' * 32)
            job.mkdir(parents=True, mode=0o700)
            package, certificate, _, archive = ReleaseStageTests().package(job)
            (job / 'manifest.json').write_text('{}')
            runtime = {key: str(job / relative) for key, relative in {
                'python': 'python-environment/bin/python', 'bun': 'tools/bun',
                'hermes': 'bin/hermes', 'source': 'hermes', 'reference': 'reference-home/.claude'}.items()}
            Path(runtime['source']).mkdir(mode=0o700)
            request = {'profile': str(profile), 'installed': str(installed), 'account_home': str(owner),
                'identifier': job.name, 'certificate': certificate, 'version': certificate['version'],
                'commit': certificate['program_commit'], 'package_sha256': sha(archive),
                'runtime_metadata_sha256': sha(job / 'manifest.json'),
                'python_lock_sha256': sha(package / 'python-runtime/uv.lock'), 'runtime': runtime,
                'runtime_fingerprint': runtime_source_fingerprint(Path(runtime['source']))}
            service_launcher = launcher
            class Services:
                def __init__(self, *arguments, **options):
                    pass
                def preview(self):
                    return {'synthetic': True}
                def _inspect(self, role):
                    return {'ExecStart': '{ path=' + str(service_launcher) + ' ; argv[]=hermes ; }'}, None
            modules = {'lifeos_installation': lifeos_installation,
                'release_version': SimpleNamespace(status=lambda *args: {'active': {'verification': 'verified'}}),
                'version_drift': SimpleNamespace(default_baseline_path=lambda home: home / 'baseline.json',
                    load_baseline=lambda *args: {'source_root': str(owner / 'source')}),
                'update_worker': SimpleNamespace(check_prior_source=lambda *args: None,
                    check_template_compatibility=lambda *args: None),
                'update_plan': SimpleNamespace(deployed_system_files=lambda *args: {},
                    plan_system_files=lambda *args: {'add': [], 'replace': [], 'remove': []}),
                'profile_services': SimpleNamespace(ProfileServices=Services),
                'update_dependencies': SimpleNamespace(_package_roots=lambda *args: set())}
            source = SimpleNamespace(memory_module=modules.__getitem__)
            # Native source planning and systemd queries are separate unit boundaries.
            with patch.dict(os.environ, HOME=str(native_home)), patch.object(release_plan, 'load_bridge', return_value=source):
                self.assertEqual(Path.home(), native_home)
                result = release_plan.inspect_operation(job, request)
                self.assertEqual(result['launchers'], [launcher])
                self.assertEqual(result['installed'], installed)
                self.assertFalse(result['fresh'])
                request['account_home'] = str(native_home)
                with self.assertRaisesRegex(ReleaseRejected, 'installation binding'):
                    release_plan.inspect_operation(job, request)
                request['account_home'] = str(owner)
                service_launcher = Path(temporary) / 'outside-hermes'
                service_launcher.write_text('#!/bin/sh\nexit 0\n')
                with self.assertRaisesRegex(ReleaseRejected, 'regular account program'):
                    release_plan.inspect_operation(job, request)
                service_launcher = launcher.with_name('alias-hermes')
                service_launcher.symlink_to(launcher)
                with self.assertRaises(ProgramConflict):
                    release_plan.inspect_operation(job, request)
            self.assertEqual((profile / lifeos_installation.SETTING).read_bytes(), selection_bytes)

    def test_dashboard_queue_launches_from_the_account_under_native_home(self):
        import inspect
        from optional.lifeos_release_manager import release_preparation
        class LaunchBoundary(Exception):
            pass
        lines, start = inspect.getsourcelines(release_preparation.queue)
        boundary = start + next(i for i, line in enumerate(lines) if 'process = subprocess.Popen(' in line)
        for relative in ('.hermes', '.hermes/profiles/work'):
            with self.subTest(profile=relative), tempfile.TemporaryDirectory() as temporary:
                owner = Path(temporary)
                profile = owner / relative
                profile.mkdir(parents=True, mode=0o700)
                native_home = owner / 'native/home'
                native_home.mkdir(parents=True, mode=0o700)
                captured = {}
                def trace(frame, event, argument):
                    if frame.f_code is release_preparation.queue.__code__ and event == 'line' and frame.f_lineno == boundary:
                        captured.update(home=frame.f_locals['home'], environment=frame.f_locals['environment'])
                        raise LaunchBoundary()
                    return trace
                previous = sys.gettrace()
                try:
                    with patch.dict(os.environ, HOME=str(native_home)):
                        sys.settrace(trace)
                        with self.assertRaises(LaunchBoundary):
                            release_preparation.queue(profile, {'intent': 'update', 'version': '0.4.3'})
                finally:
                    sys.settrace(previous)
                self.assertEqual(captured['home'], owner)
                self.assertEqual(captured['environment']['HOME'], str(owner))
                self.assertEqual(captured['environment']['HERMES_HOME'], str(profile))

    def test_cli_preparation_records_account_and_preserves_native_selection(self):
        from lifeos_hook_bridge import lifeos_installation
        from optional.lifeos_release_manager import cli, inplace_preparation
        class DownloadBoundary(Exception):
            pass
        for relative in ('.hermes', '.hermes/profiles/work'):
            with self.subTest(profile=relative), tempfile.TemporaryDirectory() as temporary:
                owner = Path(temporary)
                profile = owner / relative
                profile.mkdir(parents=True, mode=0o700)
                native_home = owner / 'native/home'
                (native_home / '.claude').mkdir(parents=True, mode=0o700)
                lifeos_installation.publish(profile, native_home, owner / 'workspace')
                selection_bytes = (profile / lifeos_installation.SETTING).read_bytes()
                (profile / 'config.yaml').write_text('model: synthetic\n')
                accounts = []
                original = inplace_preparation.account_home
                def recorded_account(selected_profile):
                    accounts.append(original(selected_profile))
                    return accounts[-1]
                class Catalog:
                    def download_integration(self, directory, version):
                        raise DownloadBoundary()
                with patch.dict(os.environ, HOME=str(native_home)), \
                        patch.object(inplace_preparation, 'account_home', side_effect=recorded_account):
                    # The test interpreter's Hermes is not an admitted host, so the compatibility check refuses
                    # before any download; the account is already selected at that point.
                    with self.assertRaisesRegex(ReleaseRejected, 'cannot be installed on this Hermes installation'):
                        cli.prepare(profile, catalog=Catalog(), intent='update')
                # The in-place request records this account; the native service HOME does not select it.
                self.assertEqual(accounts, [owner])
                self.assertEqual((profile / lifeos_installation.SETTING).read_bytes(), selection_bytes)

    def test_standard_profile_keeps_account_home_under_native_service_home(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary)
            profile = owner / '.hermes'
            profile.mkdir(mode=0o700)
            native_home = owner / 'native/home'
            native_home.mkdir(parents=True, mode=0o700)
            code = ('import json,sys;from pathlib import Path;'
                'from optional.lifeos_release_manager.release_accounts import account_home;'
                'print(json.dumps({"account":str(account_home(Path(sys.argv[1]))),"service":str(Path.home())}))')
            result = subprocess.run([sys.executable, '-B', '-c', code, str(profile)],
                env=dict(os.environ, HOME=str(native_home)), capture_output=True, text=True, check=True)
            self.assertEqual(result.stderr, '')
            self.assertEqual(json.loads(result.stdout), {'account': str(owner), 'service': str(native_home)})
            self.assertEqual(account_home(profile), owner)

    def test_named_profile_selects_its_account_not_the_native_home(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary)
            profile = owner / '.hermes/profiles/work'
            profile.mkdir(parents=True, mode=0o700)
            self.assertEqual(account_home(profile), owner)

    def test_custom_profile_preserves_explicit_home(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / 'custom-profile'
            profile.mkdir(mode=0o700)
            self.assertEqual(account_home(profile), Path.home())

    def test_account_alias_and_shared_write_permissions_refuse(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary) / 'owner'
            profile = owner / '.hermes'
            profile.mkdir(parents=True, mode=0o700)
            alias = Path(temporary) / 'alias'
            alias.symlink_to(owner, target_is_directory=True)
            with self.assertRaises(ReleaseRejected):
                account_home(alias / '.hermes')
            owner.chmod(0o770)
            with self.assertRaises(ReleaseRejected):
                account_home(profile)
            owner.chmod(0o700)

    def test_untrusted_account_refuses_before_preparation_creates_files(self):
        from optional.lifeos_release_manager import release_preparation
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary) / 'owner'
            owner.mkdir(mode=0o700)
            profile = owner / '.hermes'
            profile.mkdir(mode=0o700)
            owner.chmod(0o770)
            try:
                with self.assertRaises(ReleaseRejected):
                    release_preparation.queue(profile, {'intent': 'update', 'version': '0.4.3'})
                self.assertEqual(list(profile.iterdir()), [])
            finally:
                owner.chmod(0o700)


if __name__ == '__main__':
    unittest.main()
