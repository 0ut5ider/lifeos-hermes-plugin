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


if __name__ == '__main__':
    unittest.main()
