# ABOUTME: Checks the in-place worker's restart verification, rollback order, bytecode removal, and inventory.
# ABOUTME: Uses real user systemd units with synthetic names, real processes, real files, and real Git checkouts.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from uuid import uuid4

from optional.lifeos_release_manager import inplace_worker
from optional.lifeos_release_manager.release_catalog import ReleaseRejected
from optional.lifeos_release_manager.release_programs import ProgramTransaction, publish


PYTHON = '%d.%d' % sys.version_info[:2]


class SyntheticUnits(unittest.TestCase):
    """Starts uniquely named runtime units so the account's own Hermes services are never touched."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        suffix = uuid4().hex[:8]
        self.units = {'gateway': 'lifeos-worker-gateway-' + suffix + '.service',
                      'dashboard': 'lifeos-worker-dashboard-' + suffix + '.service'}

    def unit(self, role, *, start=True):
        path = self.root / self.units[role]
        path.write_text('[Unit]\nDescription=LifeOS synthetic worker control\n[Service]\nType=simple\n'
                        'ExecStart=' + sys.executable + ' -c "import time; time.sleep(120)"\n'
                        '[Install]\nWantedBy=default.target\n')
        subprocess.run(['systemctl', '--user', '--quiet', 'link', '--runtime', str(path)], check=True)
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        def cleanup():
            subprocess.run(['systemctl', '--user', 'stop', self.units[role]], check=False)
            subprocess.run(['systemctl', '--user', '--quiet', 'disable', '--runtime', self.units[role]], check=False)
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=False)
        self.addCleanup(cleanup)
        if start:
            subprocess.run(['systemctl', '--user', 'start', self.units[role]], check=True)
            time.sleep(0.3)
        return self.units[role]


class RestartTests(SyntheticUnits):
    def test_unit_restarted_after_the_drain_passes(self):
        unit = self.unit('gateway', start=False)
        drained = inplace_worker.boot_ticks()
        time.sleep(0.05)
        subprocess.run(['systemctl', '--user', 'start', unit], check=True)
        inplace_worker.check_restarted([unit], drained)

    def test_unit_whose_process_predates_the_drain_is_refused(self):
        unit = self.unit('gateway')
        time.sleep(0.05)
        drained = inplace_worker.boot_ticks()
        with self.assertRaisesRegex(ReleaseRejected, 'new main process'):
            inplace_worker.check_restarted([unit], drained)

    def test_stopped_unit_is_refused(self):
        unit = self.unit('gateway', start=False)
        with self.assertRaisesRegex(ReleaseRejected, 'new main process'):
            inplace_worker.check_restarted([unit], inplace_worker.boot_ticks())

    def test_unchanged_enablement_passes_and_a_changed_one_is_refused(self):
        gateway, dashboard = self.unit('gateway'), self.unit('dashboard')
        subprocess.run(['systemctl', '--user', '--quiet', 'enable', '--runtime', dashboard], check=True)
        recorded = {gateway: 'linked-runtime', dashboard: 'enabled-runtime'}
        inplace_worker.check_enabled(recorded)
        subprocess.run(['systemctl', '--user', '--quiet', 'disable', '--runtime', dashboard], check=True)
        subprocess.run(['systemctl', '--user', '--quiet', 'link', '--runtime', str(self.root / dashboard)], check=True)
        with self.assertRaisesRegex(ReleaseRejected, dashboard):
            inplace_worker.check_enabled(recorded)


class VerifyRestartTests(SyntheticUnits):
    def setUp(self):
        super().setUp()
        self.profile = self.root / '.hermes'
        self.profile.mkdir(mode=0o700)
        self.source = self.root / 'hermes-agent'
        (self.source / 'hermes_cli').mkdir(parents=True)
        (self.source / 'hermes_cli/__init__.py').write_text('')
        (self.source / 'hermes_cli/plugins.py').write_text("VALID_HOOKS = {'pre_turn_stop'}\n")
        (self.source / 'hermes_cli/middleware.py').write_text('REQUIRED_MIDDLEWARE_API_VERSION = 1\n')
        self.before = b'memory:\n  provider: builtin\n'
        (self.profile / 'config.yaml').write_bytes(self.before)
        self.request = {'format': 2, 'profile': str(self.profile), 'account_home': str(self.root),
                        'host': {'source': str(self.source)}, 'runtime': {'bun': str(self.root / 'tools/bun')}}
        self.entry = {'label': 'v0.0.1', 'python': PYTHON,
                      'capabilities': {'hooks': ['pre_turn_stop'], 'middleware_api': 1}}
        self.gateway = self.unit('gateway', start=False)
        self.plan = {'services': {'roles': ['gateway'], 'created': [], 'enabled': {'gateway': 'linked-runtime'}}}
        self.drained = inplace_worker.boot_ticks()
        time.sleep(0.05)
        subprocess.run(['systemctl', '--user', 'start', self.gateway], check=True)

    def verify(self, *, fresh=False):
        inplace_worker.verify_restart(self.request, self.plan, self.entry, ['gateway'], self.drained, self.before,
                                      fresh=fresh, python=sys.executable, units=self.units)

    def test_restarted_patched_host_with_unchanged_memory_provider_passes(self):
        self.verify()

    def test_changed_memory_provider_is_refused_unless_fresh(self):
        (self.profile / 'config.yaml').write_bytes(b'memory:\n  provider: lifeos\n')
        with self.assertRaisesRegex(ReleaseRejected, 'memory.provider'):
            self.verify()
        self.verify(fresh=True)

    def test_host_without_the_patched_hooks_is_refused(self):
        (self.source / 'hermes_cli/plugins.py').write_text("VALID_HOOKS = {'pre_tool_call'}\n")
        with self.assertRaisesRegex(ReleaseRejected, 'pre_turn_stop'):
            self.verify()

    def test_changed_enablement_is_refused(self):
        self.plan['services']['enabled'] = {'gateway': 'enabled-runtime'}
        with self.assertRaisesRegex(ReleaseRejected, 'starts with your account'):
            self.verify()

    def test_unit_that_did_not_restart_is_refused(self):
        self.drained = inplace_worker.boot_ticks()
        with self.assertRaisesRegex(ReleaseRejected, 'new main process'):
            self.verify()


class VerifyRuntimeTests(unittest.TestCase):
    """Runs a real launcher script that answers ``config check`` and ``lifeos-version`` like Hermes."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name).resolve()
        self.profile = root / '.hermes'
        job = self.profile / '.lifeos-releases' / ('a' * 32)
        job.mkdir(parents=True, mode=0o700)
        self.report = root / 'report.json'
        launcher = root / 'hermes'
        launcher.write_text('#!/bin/sh\nif [ "$1" = lifeos-version ]; then cat ' + str(self.report) + '; fi\n')
        launcher.chmod(0o755)
        publish(job / 'plan.json', json.dumps({'launchers': [str(launcher)]}).encode())
        self.identity = {'version': '0.8.0', 'commit': 'c' * 40, 'package_sha256': 'd' * 64}
        self.request = {'format': 2, 'profile': str(self.profile), 'account_home': str(root), 'identifier': job.name,
                        'runtime': {'hermes': str(launcher), 'bun': str(root / 'tools/bun')}, **self.identity}

    def verify(self, host):
        from optional.lifeos_release_manager.release_plan import verify_runtime
        self.report.write_text(json.dumps({'active': {'verification': 'verified', **self.identity}, 'host': host}))
        verify_runtime(self.request)

    def test_installed_host_passes(self):
        self.verify({'state': 'installed', 'source': '/h', 'changed': []})

    def test_host_drift_is_refused_with_the_changed_paths(self):
        with self.assertRaisesRegex(ReleaseRejected, 'hermes_cli/plugins.py'):
            self.verify({'state': 'host_drift', 'source': '/h', 'changed': ['hermes_cli/plugins.py']})


class RollbackTests(unittest.TestCase):
    """Publishes a real program transaction over real files, then rolls it back through the worker."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.job = self.root / 'job'
        self.job.mkdir(mode=0o700)
        self.target = self.root / 'hermes-agent/hermes_cli/plugins.py'
        self.target.parent.mkdir(parents=True)
        self.target.write_text('stock\n')
        self.added = self.target.with_name('new_hook.py')
        patched, added = self.root / 'patched.py', self.root / 'added.py'
        patched.write_text('patched\n')
        added.write_text('added\n')
        self.programs = ProgramTransaction(self.job / 'program-snapshot')
        self.programs.prepare(directories={}, files={self.target: patched, self.added: added})
        self.programs.apply()
        self.order = []
        self.request = {'host': {'source': str(self.target.parents[1])}}
        self.plan = {'services': {'created': []}}

    def services(self, state='stopped'):
        order, outer = self.order, self

        class Services:
            def status(self):
                return {'state': state}

            def quiesce(self):
                order.append('services-stopped')

            def resume(self):
                order.append(('services-resumed', outer.target.read_text(), outer.added.exists()))

        return Services()

    def rollback(self, synchronize, services=None):
        def reload(*arguments):
            self.order.append((' '.join(arguments), self.target.read_text(), self.added.exists()))
        def mount():
            self.order.append(('mount', self.target.read_text()))
        with mock.patch.object(inplace_worker, '_systemctl', side_effect=reload), \
                mock.patch.object(inplace_worker, 'synchronize', side_effect=synchronize):
            return inplace_worker._rollback(self.job, self.request, self.plan,
                                            self.services() if services is None else services, self.programs, mount)

    def test_rollback_restores_mount_programs_reload_dependencies_then_services(self):
        def synchronize(job, request, *, label):
            self.order.append((label, self.target.read_text()))
            return {'lock_sha256': 'a' * 64}
        self.assertTrue(self.rollback(synchronize))
        self.assertEqual(self.order, ['services-stopped', ('mount', 'patched\n'), ('daemon-reload', 'stock\n', False),
                                      ('dependency-restore', 'stock\n'), ('services-resumed', 'stock\n', False)])
        self.assertFalse((self.job / 'dependency-restore-failure.json').exists())

    def test_services_without_a_drain_journal_are_neither_stopped_nor_resumed(self):
        def synchronize(job, request, *, label):
            return {'lock_sha256': 'a' * 64}
        self.request['host']['transition_units'] = {'gateway': {'before': 'b' * 64, 'after': 'c' * 64}}
        self.assertTrue(self.rollback(synchronize, services=self.services('none')))
        self.assertEqual(self.order, [('mount', 'patched\n'), ('daemon-reload', 'stock\n', False)])

    def test_failed_dependency_restore_is_recorded_and_services_still_resume(self):
        def synchronize(job, request, *, label):
            raise ReleaseRejected('Hermes cannot build the environment')
        self.assertFalse(self.rollback(synchronize))
        self.assertEqual(self.order[-1], ('services-resumed', 'stock\n', False))
        self.assertEqual(json.loads((self.job / 'dependency-restore-failure.json').read_text()),
                         {'error': 'ReleaseRejected'})


class BytecodeTests(unittest.TestCase):
    def test_only_the_cached_bytecode_of_changed_source_modules_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'hermes-agent'
            cache = source / 'hermes_cli/__pycache__'
            cache.mkdir(parents=True)
            for name in ('plugins.cpython-314.pyc', 'plugins.cpython-314.opt-1.pyc', 'plugins_extra.cpython-314.pyc',
                         'config.cpython-314.pyc'):
                (cache / name).write_bytes(b'compiled')
            outside = Path(directory) / 'elsewhere/__pycache__'
            outside.mkdir(parents=True)
            (outside / 'plugins.cpython-314.pyc').write_bytes(b'compiled')
            inplace_worker.clear_bytecode({'host': {'source': str(source)}},
                                          [str(source / 'hermes_cli/plugins.py'), str(source / 'scripts/run.sh'),
                                           str(Path(directory) / 'elsewhere/plugins.py')])
            self.assertEqual(sorted(path.name for path in cache.iterdir()),
                             ['config.cpython-314.pyc', 'plugins_extra.cpython-314.pyc'])
            self.assertTrue((outside / 'plugins.cpython-314.pyc').exists())


class InventorySnapshotTests(unittest.TestCase):
    def test_snapshot_records_other_plugins_enablement_and_packages_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile, source = root / '.hermes', root / 'hermes-agent'
            for name in ('weather', 'lifeos-hook-bridge'):
                (profile / 'plugins' / name).mkdir(parents=True)
                (profile / 'plugins' / name / 'plugin.yaml').write_text('name: ' + name + '\n')
            (profile / 'config.yaml').write_text('plugins:\n  enabled: [weather, lifeos-hook-bridge]\n')
            source.mkdir()
            (source / 'uv.lock').write_text('version = 1\n[[package]]\nname = "mcp"\nversion = "2.0.0"\n'
                                            'source = { registry = "https://pypi.org/simple" }\n'
                                            '[[package]]\nname = "hermes-agent"\nversion = "0.21.7"\n'
                                            'source = { editable = "." }\n')
            request = {'profile': str(profile), 'host': {'source': str(source)}}
            before = inplace_worker.inventory_snapshot(request)
            self.assertEqual(sorted(before['plugins']), ['weather'])
            self.assertEqual(before['enabled'], ['weather'])
            self.assertEqual(before['packages'], {'mcp': ['2.0.0']})
            (profile / 'plugins/lifeos-hook-bridge/plugin.yaml').write_text('name: changed by the operation\n')
            inplace_worker.check_inventory(before, inplace_worker.inventory_snapshot(request), {})
            (profile / 'plugins/weather/plugin.yaml').write_text('name: weather\nversion: 2\n')
            with self.assertRaisesRegex(ReleaseRejected, 'another Hermes plugin'):
                inplace_worker.check_inventory(before, inplace_worker.inventory_snapshot(request), {})


class CreatedUnitsTests(unittest.TestCase):
    def test_created_units_are_the_standard_gateway_and_dashboard_units(self):
        self.assertEqual(inplace_worker.CREATED_UNITS,
                         {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service'})


class ConsumersStoppedTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.source = root / 'hermes-agent'
        self.source.mkdir()
        self.state = root / 'installs/0123456789abcdef'
        self.state.mkdir(parents=True)
        self.request = {'host': {'source': str(self.source), 'state_directory': str(self.state)}}

    def process(self, *arguments):
        """Start a detached Hermes-like process that this test does not parent, like a hand-started consumer."""
        command = ' '.join([sys.executable, '-c', '"import time; time.sleep(120)"', *arguments])
        launched = subprocess.run(['/bin/sh', '-c', command + ' >/dev/null 2>&1 & echo $!'], capture_output=True,
                                  text=True, check=True, env={**os.environ, 'PYTHONPATH': str(self.source)})
        pid = int(launched.stdout)
        def stop():
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
        self.addCleanup(stop)
        time.sleep(0.3)
        return pid

    def test_reviewed_hand_started_dashboard_is_stopped_for_its_created_unit(self):
        from optional.lifeos_release_manager.inplace_services import inventory
        pid = self.process('dashboard')
        consumers = inventory(self.source, self.state)['consumers']
        self.assertEqual([item['pid'] for item in consumers], [pid])
        inplace_worker._consumers_stopped(self.request, {'services': {'created': ['dashboard'], 'consumers': consumers}})
        self.assertFalse(Path('/proc', str(pid)).exists())

    def test_remaining_consumer_refuses_with_its_process(self):
        pid = self.process('chat')
        with self.assertRaisesRegex(ReleaseRejected, 'still use the installation: .*' + str(pid)):
            inplace_worker._consumers_stopped(self.request, {'services': {'created': [], 'consumers': []}})
        self.assertTrue(Path('/proc', str(pid)).exists())


class RegistrationTests(SyntheticUnits):
    """A synthetic gateway unit writes a real registration receipt through the bridge's own module."""

    def setUp(self):
        super().setUp()
        import shutil
        repository = Path(__file__).resolve().parents[1]
        self.profile = self.root / '.hermes'
        shutil.copytree(repository / 'lifeos_hook_bridge', self.profile / 'plugins/lifeos-hook-bridge',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        self.source = self.root / 'hermes-agent'
        (self.source / 'hermes_cli').mkdir(parents=True)
        (self.source / 'hermes_cli/__init__.py').write_text('')
        self.request = {'profile': str(self.profile), 'host': {'source': str(self.source)}}

    def gateway(self, mode):
        script = self.root / 'gateway.py'
        script.write_text('import importlib.util, sys, time\nsys.path.insert(0, sys.argv[1])\n'
                          'spec = importlib.util.spec_from_file_location("registration", sys.argv[2])\n'
                          'module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n'
                          'module.write_receipt(sys.argv[3], sys.argv[4])\ntime.sleep(120)\n')
        unit = self.root / self.units['gateway']
        unit.write_text('[Service]\nType=simple\nExecStart=' + sys.executable + ' -B ' + str(script) + ' ' + str(self.source)
                        + ' ' + str(self.profile / 'plugins/lifeos-hook-bridge/registration.py') + ' ' + str(self.profile)
                        + ' ' + mode + '\n')
        subprocess.run(['systemctl', '--user', '--quiet', 'link', '--runtime', str(unit)], check=True)
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        def cleanup():
            subprocess.run(['systemctl', '--user', 'stop', self.units['gateway']], check=False)
            subprocess.run(['systemctl', '--user', '--quiet', 'disable', '--runtime', self.units['gateway']], check=False)
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=False)
        self.addCleanup(cleanup)
        subprocess.run(['systemctl', '--user', 'start', self.units['gateway']], check=True)

    def verify(self, plan=None):
        plan = plan or {'services': {'roles': ['gateway'], 'created': [], 'active': {'gateway': True}}}
        return inplace_worker.verify_registration(self.request, plan, unit=self.units['gateway'])

    def test_patched_receipt_from_the_installed_checkout_is_returned(self):
        self.gateway('patched')
        receipt = self.verify()
        self.assertEqual((receipt['mode'], receipt['source']), ('patched', str(self.source.resolve())))

    def test_reduced_registration_is_refused(self):
        self.gateway('reduced')
        with self.assertRaisesRegex(ReleaseRejected, 'without the patched host hooks'):
            self.verify()

    def test_gateway_that_did_not_run_before_may_stay_stopped(self):
        self.unit('gateway', start=False)
        self.assertIsNone(self.verify({'services': {'roles': ['gateway'], 'created': [], 'active': {'gateway': False}}}))
        with self.assertRaisesRegex(ReleaseRejected, 'does not run after the operation'):
            self.verify()

    def test_profile_without_a_gateway_role_needs_no_receipt(self):
        self.assertIsNone(self.verify({'services': {'roles': [], 'created': [], 'active': {}}}))


if __name__ == '__main__':
    unittest.main()
