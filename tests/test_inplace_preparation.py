# ABOUTME: Checks the in-place preparation helpers that choose host files and build the preview tree.
# ABOUTME: Uses disposable real Git checkouts; the owner's checkout must remain unchanged.
from pathlib import Path
import subprocess
import tempfile
import unittest

from optional.lifeos_release_manager.inplace_preparation import build_preview, desired_host_files


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


class DesiredHostFilesTests(unittest.TestCase):
    def test_new_entry_targets_receive_their_patched_files(self):
        staged = {'a.py': {'stock': Path('/s/a.py'), 'patched': Path('/p/a.py')}}
        self.assertEqual(desired_host_files({}, staged), {'a.py': Path('/p/a.py')})

    def test_targets_only_the_recorded_release_changed_return_to_their_originals(self):
        staged = {'a.py': {'stock': Path('/s/a.py'), 'patched': Path('/p/a.py')}}
        record = {'files': {'a.py': {'stock': 'x', 'patched': 'y'}, 'b.py': {'stock': 'x', 'patched': 'y'},
                            'added.py': {'stock': None, 'patched': 'y'}}}
        self.assertEqual(desired_host_files({}, staged, record, {'a.py': Path('/o/a.py'), 'b.py': Path('/o/b.py')}),
                         {'a.py': Path('/p/a.py'), 'b.py': Path('/o/b.py'), 'added.py': None})


class PreviewTests(unittest.TestCase):
    def test_preview_copies_tracked_files_and_overlays_the_desired_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'hermes-agent'
            (source / 'hermes_cli').mkdir(parents=True)
            git('init', '-q', cwd=source)
            (source / 'hermes_cli/plugins.py').write_text('stock\n')
            (source / 'run.sh').write_text('#!/bin/sh\n')
            (source / 'run.sh').chmod(0o755)
            (source / 'removed.py').write_text('added by the last release\n')
            (source / '.gitignore').write_text('venv/\n')
            git('add', '.', cwd=source)
            git('-c', 'user.name=T', '-c', 'user.email=t@example.invalid', 'commit', '-qm', 'base', cwd=source)
            (source / 'venv').mkdir()
            (source / 'venv/ignored').write_text('not copied\n')
            patched = root / 'patched.py'
            patched.write_text('patched\n')
            added = root / 'new_hook.py'
            added.write_text('added\n')
            (root / 'job').mkdir()
            preview = build_preview(source, {'hermes_cli/plugins.py': patched, 'hermes_cli/new_hook.py': added,
                                             'removed.py': None}, root / 'job/hermes-preview')
            self.assertEqual((preview / 'hermes_cli/plugins.py').read_text(), 'patched\n')
            self.assertEqual((preview / 'hermes_cli/new_hook.py').read_text(), 'added\n')
            self.assertFalse((preview / 'removed.py').exists())
            self.assertFalse((preview / 'venv').exists())
            self.assertTrue((preview / 'run.sh').stat().st_mode & 0o100)
            self.assertEqual((source / 'hermes_cli/plugins.py').read_text(), 'stock\n')
            self.assertEqual(git('status', '--porcelain', cwd=source), '')


if __name__ == '__main__':
    unittest.main()


class StockSourceTests(unittest.TestCase):
    def test_originals_and_untouched_host_files_form_the_stock_source(self):
        from optional.lifeos_release_manager.inplace_preparation import stock_source
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'host/hermes_cli').mkdir(parents=True)
            (root / 'host/hermes_cli/plugins.py').write_text('patched by the recorded release\n')
            (root / 'host/hermes_cli/other.py').write_text('stock and untouched\n')
            (root / 'originals/hermes_cli').mkdir(parents=True)
            (root / 'originals/hermes_cli/plugins.py').write_text('original\n')
            entry = {'files': {'hermes_cli/plugins.py': {'stock': 'a', 'patched': 'b'},
                               'hermes_cli/other.py': {'stock': 'c', 'patched': 'd'},
                               'hermes_cli/new.py': {'stock': None, 'patched': 'e'}}}
            record = {'files': {'hermes_cli/plugins.py': {'stock': 'a', 'patched': 'b'},
                                'hermes_cli/new.py': {'stock': None, 'patched': 'e'}}}
            originals = {'hermes_cli/plugins.py': root / 'originals/hermes_cli/plugins.py'}
            result = stock_source(root / 'host', record, originals, entry, root / 'stock')
            self.assertEqual((result / 'hermes_cli/plugins.py').read_text(), 'original\n')
            self.assertEqual((result / 'hermes_cli/other.py').read_text(), 'stock and untouched\n')
            self.assertFalse((result / 'hermes_cli/new.py').exists())


class InventoryTests(unittest.TestCase):
    def test_inventory_changes_outside_the_review_are_refused(self):
        from optional.lifeos_release_manager.inplace_worker import check_inventory
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        before = {'plugins': {'weather': 'a'}, 'enabled': ['weather'], 'packages': {'mcp': ['2.0.0']}}
        after = {'plugins': {'weather': 'a'}, 'enabled': ['weather'],
                 'packages': {'mcp': ['2.0.0'], 'tree-sitter': ['0.26.0']}}
        check_inventory(before, after, {'tree-sitter': ['0.26.0']})
        for changed in ({**after, 'plugins': {'weather': 'b'}}, {**after, 'enabled': []},
                        {**after, 'packages': {'mcp': ['2.1.0'], 'tree-sitter': ['0.26.0']}},
                        {**after, 'packages': {**after['packages'], 'six': ['1.0']}}):
            with self.subTest(changed=changed), self.assertRaises(ReleaseRejected):
                check_inventory(before, changed, {'tree-sitter': ['0.26.0']})


class TransitionTests(unittest.TestCase):
    def test_only_a_managed_job_runtime_has_a_transition_target(self):
        from optional.lifeos_release_manager.host_compatibility import transition_source
        profile = Path('/home/owner/.hermes')
        self.assertEqual(transition_source(profile, profile / '.lifeos-releases' / ('a' * 32) / 'hermes'),
                         profile / 'hermes-agent')
        for source in (profile / 'hermes-agent', profile / '.lifeos-releases/short/hermes',
                       profile / '.lifeos-releases' / ('a' * 32) / 'package/hermes', Path('/usr/local/lib/hermes-agent')):
            with self.subTest(source=source):
                self.assertIsNone(transition_source(profile, source))

    def test_transition_gateway_unit_is_the_stock_generated_definition(self):
        import hashlib, sys
        import hermes_cli
        from optional.lifeos_release_manager.inplace_preparation import transition_gateway_unit
        source = Path(hermes_cli.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            profile, job = home / '.hermes', home / 'job'
            profile.mkdir()
            job.mkdir()
            unit = home / '.config/systemd/user/hermes-gateway.service'
            unit.parent.mkdir(parents=True)
            unit.write_text('[Service]\nExecStart=' + str(profile / '.lifeos-releases' / ('a' * 32)) + '/hermes/bin gateway run\n'
                            'WorkingDirectory=' + str(profile) + '\nKillMode=mixed\n')
            value = transition_gateway_unit(Path(sys.executable), source, profile, home, job)
            text = (job / 'transition-gateway.service').read_text()
            self.assertIn("sys.path.insert(0, '" + str(source) + "')", text)
            self.assertIn('Environment="HERMES_HOME=' + str(profile) + '"', text)
            self.assertNotIn('.lifeos-releases', text)
            self.assertEqual(value, {'gateway': {'before': hashlib.sha256(unit.read_bytes()).hexdigest(),
                                                 'after': hashlib.sha256(text.encode()).hexdigest()}})

    def test_transition_without_a_gateway_unit_replaces_no_unit(self):
        import sys
        import hermes_cli
        from optional.lifeos_release_manager.inplace_preparation import transition_gateway_unit
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.hermes').mkdir()
            self.assertEqual(transition_gateway_unit(Path(sys.executable), Path(hermes_cli.__file__).resolve().parents[1],
                                                     home / '.hermes', home, home), {})

    def test_transition_refuses_another_unit_that_runs_the_managed_runtime(self):
        import sys
        import hermes_cli
        from optional.lifeos_release_manager.inplace_preparation import transition_gateway_unit
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.hermes').mkdir()
            unit = home / '.config/systemd/user/hermes-dashboard.service'
            unit.parent.mkdir(parents=True)
            unit.write_text('[Service]\nExecStart=' + str(home / '.hermes/.lifeos-releases' / ('a' * 32)) + '/hermes/bin dashboard\n')
            with self.assertRaisesRegex(ReleaseRejected, 'hermes-dashboard.service'):
                transition_gateway_unit(Path(sys.executable), Path(hermes_cli.__file__).resolve().parents[1],
                                        home / '.hermes', home, home)

    def _transition_home(self, directory, gateway, drop_in=None):
        home = Path(directory)
        (home / '.hermes').mkdir()
        unit = home / '.config/systemd/user/hermes-gateway.service'
        unit.parent.mkdir(parents=True)
        unit.write_text(gateway)
        if drop_in is not None:
            (unit.parent / 'hermes-gateway.service.d').mkdir()
            (unit.parent / 'hermes-gateway.service.d/override.conf').write_text(drop_in)
        return home

    def _generate(self, home):
        import sys
        import hermes_cli
        from optional.lifeos_release_manager.inplace_preparation import transition_gateway_unit
        return transition_gateway_unit(Path(sys.executable), Path(hermes_cli.__file__).resolve().parents[1],
                                       home / '.hermes', home, home)

    def test_transition_keeps_a_gateway_unit_that_runs_the_account_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            home = self._transition_home(directory, '[Service]\nExecStart=/home/owner/.local/bin/hermes gateway run\n'
                                         'KillMode=control-group\n')
            self.assertEqual(self._generate(home), {})

    def test_transition_refuses_a_managed_unit_whose_kill_mode_differs_from_stock(self):
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            managed = str(home / '.hermes/.lifeos-releases' / ('a' * 32)) + '/hermes/.hermes/bin/hermes'
            home = self._transition_home(directory, '[Service]\nExecStart=' + managed + ' gateway run\n'
                                         'WorkingDirectory=' + str(home / '.hermes') + '\nKillMode=control-group\n')
            with self.assertRaisesRegex(ReleaseRejected, 'KillMode'):
                self._generate(home)

    def test_transition_refuses_a_drop_in_that_runs_the_managed_runtime(self):
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            managed = str(home / '.hermes/.lifeos-releases' / ('a' * 32)) + '/hermes/.hermes/bin/hermes'
            home = self._transition_home(directory, '[Service]\nExecStart=/home/owner/.local/bin/hermes gateway run\n',
                                         '[Service]\nExecStart=\nExecStart=' + managed + ' gateway run\n')
            with self.assertRaisesRegex(ReleaseRejected, 'override.conf'):
                self._generate(home)

    def test_transition_refuses_a_symlinked_gateway_unit(self):
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with tempfile.TemporaryDirectory() as directory:
            home = self._transition_home(directory, '[Service]\n')
            unit = home / '.config/systemd/user/hermes-gateway.service'
            target = home / 'elsewhere.service'
            unit.rename(target)
            unit.symlink_to(target)
            with self.assertRaisesRegex(ReleaseRejected, 'regular file'):
                self._generate(home)

    def test_transition_unit_files_publish_only_the_reviewed_unit(self):
        import hashlib
        from optional.lifeos_release_manager.inplace_plan import transition_unit_files
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with tempfile.TemporaryDirectory() as directory:
            home, job = Path(directory), Path(directory) / 'job'
            job.mkdir()
            (job / 'transition-gateway.service').write_text('[Service]\n')
            digest = hashlib.sha256(b'[Service]\n').hexdigest()
            units = {'gateway': {'before': 'b' * 64, 'after': digest}}
            self.assertEqual(transition_unit_files(home, job, units),
                             {home / '.config/systemd/user/hermes-gateway.service': job / 'transition-gateway.service'})
            (job / 'transition-gateway.service').write_text('[Service]\nExecStart=/other\n')
            with self.assertRaisesRegex(ReleaseRejected, 'reviewed'):
                transition_unit_files(home, job, units)
            self.assertEqual(transition_unit_files(home, job, {}), {})

    def test_gateway_receipt_must_come_from_the_installed_checkout(self):
        from optional.lifeos_release_manager.inplace_worker import check_receipt
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        request = {'host': {'source': '/home/owner/.hermes/hermes-agent'}}
        receipt = {'pid': 7, 'start_time': 1, 'mode': 'patched', 'source': '/home/owner/.hermes/hermes-agent'}
        self.assertEqual(check_receipt(receipt, request), receipt)
        managed = {**receipt, 'source': '/home/owner/.hermes/.lifeos-releases/' + 'a' * 32 + '/hermes'}
        for value, message in (({**receipt, 'mode': 'reduced'}, 'patched'), (managed, 'checkout'),
                               ({key: item for key, item in receipt.items() if key != 'source'}, 'checkout')):
            with self.subTest(value=value), self.assertRaisesRegex(ReleaseRejected, message):
                check_receipt(value, request)

    def test_transition_adopts_the_reviewed_units_of_the_bound_roles(self):
        from optional.lifeos_release_manager.inplace_worker import adopt_units
        calls = []
        class Services:
            units = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service'}
            def status(self):
                return {'state': 'stopped'}
            def adopt_definition(self, role, allowed):
                calls.append((role, allowed))
        units = {'gateway': {'before': 'b' * 64, 'after': 'a' * 64}}
        reloads = []
        from unittest import mock
        with mock.patch('optional.lifeos_release_manager.inplace_worker._systemctl', side_effect=lambda *args: reloads.append(args)):
            adopt_units(Services(), {'host': {'transition_units': units}})
        # A replaced unit file reports NeedDaemonReload until the manager reloads, so adoption reloads first.
        self.assertEqual(reloads, [('daemon-reload',)])
        self.assertEqual(calls, [('gateway', {'b' * 64, 'a' * 64})])
        calls.clear()
        adopt_units(Services(), {'host': {}})
        adopt_units(None, {'host': {'transition_units': units}})
        self.assertEqual(calls, [])

    def test_transition_repoints_the_service_launchers_of_the_managed_release(self):
        import json
        from optional.lifeos_release_manager.inplace_preparation import managed_service_launchers
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            job = home / '.hermes/.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True)
            workspace = home / 'workspace/hermes-agent/.hermes/bin/hermes'
            workspace.parent.mkdir(parents=True)
            workspace.write_text('#!/bin/sh\nexec ' + str(job) + '/bin/hermes "$@"\n')
            account = home / '.local/bin/hermes'
            (job / 'plan.json').write_text(json.dumps({'launchers': [str(workspace), str(account)]}))
            self.assertEqual(managed_service_launchers(job, home), [str(workspace)])
            workspace.write_text('#!/bin/sh\nexec /usr/bin/hermes "$@"\n')
            with self.assertRaisesRegex(ReleaseRejected, 'workspace'):
                managed_service_launchers(job, home)

    def test_service_value_reads_only_the_service_section(self):
        from optional.lifeos_release_manager.inplace_preparation import _service_value
        text = '[Unit]\nKillMode=mixed\n[Service]\nExecStart=/bin/true\n[Install]\nWorkingDirectory=/tmp\n'
        self.assertEqual(_service_value(text, 'KillMode', 'control-group'), 'control-group')
        self.assertEqual(_service_value(text, 'WorkingDirectory', ''), '')
        self.assertEqual(_service_value('[Service]\nKillMode=mixed\nKillMode=process\n', 'KillMode', 'control-group'), 'process')

    def test_managed_release_without_a_launcher_record_refuses(self):
        import json
        from optional.lifeos_release_manager.inplace_preparation import managed_service_launchers
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / 'job'
            job.mkdir()
            with self.assertRaisesRegex(ReleaseRejected, 'plan record'):
                managed_service_launchers(job, Path(directory))
            (job / 'plan.json').write_text(json.dumps({}))
            with self.assertRaisesRegex(ReleaseRejected, 'plan record'):
                managed_service_launchers(job, Path(directory))

    def test_transition_publishes_a_stock_forwarder_at_each_service_launcher(self):
        from optional.lifeos_release_manager.inplace_plan import transition_launchers
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory)
            service = '/home/owner/workspace/hermes-agent/.hermes/bin/hermes'
            files = transition_launchers(Path('/home/owner'), Path('/home/owner/.hermes/hermes-agent'), generated,
                                         services=[service])
            self.assertEqual(files[Path(service)].read_text(),
                             '#!/bin/sh\nexec /home/owner/.hermes/hermes-agent/.hermes/bin/hermes "$@"\n')

    def test_transition_launchers_match_the_stock_forwarders(self):
        from optional.lifeos_release_manager.inplace_plan import transition_launchers
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory)
            files = transition_launchers(Path('/home/owner'), Path('/home/owner/.hermes/hermes-agent'), generated)
            self.assertEqual(sorted(path.name for path in files), ['hermes', 'hermes-acp', 'hermes-agent'])
            expected = {'hermes': 'exec /home/owner/.hermes/hermes-agent/.hermes/bin/hermes "$@"\n',
                        'hermes-agent': 'exec /home/owner/.hermes/hermes-agent/.hermes/bin/hermes --run-module run_agent "$@"\n',
                        'hermes-acp': 'exec /home/owner/.hermes/hermes-agent/.hermes/bin/hermes-acp "$@"\n'}
            for target, source in files.items():
                self.assertEqual(source.read_text(), '#!/bin/sh\n' + expected[target.name])
                self.assertEqual(source.stat().st_mode & 0o777, 0o755)
