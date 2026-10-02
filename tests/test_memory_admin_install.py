# ABOUTME: Verifies authenticated managed finalization and detached update mount authority.
# ABOUTME: Uses native Bun mounting, real Hermes config checks, and synthetic installation data.
import json
import os
from pathlib import Path
import shlex
import sys
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.install_source import IncompatibleLifeOS, finalize_lifeos, prepare_lifeos
from lifeos_hook_bridge.version_drift import create_baseline, save_baseline
from lifeos_hook_bridge import update_worker
import test_memory_administration as admin_fixture
import test_lifeos_install_source as source_fixture


HOST = Path(os.environ.get('LIFEOS_HERMES_SOURCE', str(Path.home() /
    '.cache/lifeos-plugin-memory/source-gate-20261001-prompt-publication-release/hermes')))


class MemoryAdminInstallTests(unittest.TestCase):
    def setUp(self):
        self.fixture = admin_fixture.MemoryAdministrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.profile = self.fixture.root, self.fixture.profile
        source = self.profile / 'source-fixture'
        source.mkdir()
        upstream, self.revision, self.patches = source_fixture.InstallSourceTests().fixture(source)
        constitution = upstream / 'LifeOS/install/LIFEOS/LIFEOS_SYSTEM_PROMPT.md'
        constitution.write_text((self.root / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md').read_text())
        source_fixture.git('add', 'LifeOS', cwd=upstream)
        source_fixture.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                           'commit', '-qm', 'synthetic constitution', cwd=upstream)
        self.revision = source_fixture.git('rev-parse', 'HEAD', cwd=upstream)
        self.candidate = source / 'candidate'
        prepare_lifeos(str(upstream), self.candidate, self.revision, self.patches, ('lifeos-test.patch',))
        (self.root / 'LIFEOS/VERSION').write_text('7.40.5\n')
        self.hermes = self.profile / 'bin/hermes'
        self.hermes.parent.mkdir()
        self.hermes.write_text('#!/bin/sh\n# ABOUTME: Executes the pinned Hermes CLI in a synthetic profile.\n'
            '# ABOUTME: Uses the isolated Python environment for configuration validation.\n'
            'exec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(HOST / 'hermes_cli/main.py')) + ' "$@"\n')
        self.hermes.chmod(0o755)
        self.baseline = self.profile / 'state/baseline.json'

    def finalize(self, authorization=None):
        return finalize_lifeos(self.candidate, self.root, self.profile, self.baseline,
            self.fixture.fixture.memory.bun, str(self.hermes), self.revision, self.patches,
            ('lifeos-test.patch',), create_baseline, save_baseline, memory_authorization=authorization)

    def test_managed_finalization_runs_native_mount_and_real_config_check(self):
        with self.fixture.admin().lease(self.fixture.configuration, 'dashboard:owner') as authorization:
            result = self.finalize(authorization)
        self.assertTrue(result['mounted'])
        self.assertTrue(result['baseline_created'])
        self.assertFalse(authorization.exists())
        self.assertIn('SyntheticSafetyDoctrine', (self.profile / 'SOUL.md').read_text())
        baseline = json.loads(self.baseline.read_text())
        self.assertEqual(baseline['source_commit'], self.revision)
        self.assertEqual(baseline['installed_root'], str(self.root))
        self.assertFalse(self.fixture.configuration.load().get('ownership_enabled', False))

    def test_missing_authority_refuses_before_mount_or_snapshot(self):
        original = (self.profile / 'config.yaml').read_bytes()
        with self.assertRaises(PermissionError):
            self.finalize()
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), original)
        self.assertFalse((self.profile / 'SOUL.md').exists())
        self.assertFalse(self.baseline.exists())

    def test_late_check_failure_restores_mount_files_and_revokes_authority(self):
        self.hermes.write_text('#!/bin/sh\nexit 23\n')
        config = (self.profile / 'config.yaml').read_bytes()
        (self.profile / 'SOUL.md').write_text('SyntheticPreviousPrompt\n')
        with self.assertRaisesRegex(IncompatibleLifeOS, 'Hermes config check'), \
             self.fixture.admin().lease(self.fixture.configuration, 'dashboard:owner') as authorization:
            self.finalize(authorization)
        self.assertFalse(authorization.exists())
        self.assertEqual((self.profile / 'config.yaml').read_bytes(), config)
        self.assertEqual((self.profile / 'SOUL.md').read_text(), 'SyntheticPreviousPrompt\n')
        self.assertFalse((self.profile / 'plugins/lifeos').exists())
        self.assertFalse(self.baseline.exists())

    def request(self):
        return {'installed': str(self.root), 'hermes_home': str(self.profile), 'baseline': str(self.baseline),
            'candidate': str(self.candidate), 'prior_source': str(self.candidate / 'LifeOS/install'),
            'candidate_commit': self.revision, 'hermes_command': str(self.hermes)}

    def test_update_runtime_mounts_the_fixed_profile_with_bound_authority(self):
        request = self.request()
        job = self.profile / 'update-job'
        job.mkdir(mode=0o700)
        authorization = self.fixture.issue(binding=self.fixture.admin().job_binding(job, request, 'apply'))
        self.addCleanup(self.fixture.admin().revoke, self.fixture.configuration, authorization)
        request['memory_authorization'] = str(authorization)
        # Systemd lifecycle acceptance remains separate; the mount and configuration programs are real.
        with patch.object(update_worker, '_check_gateway_launcher'), patch.object(update_worker, '_gateway_pid', return_value='123'):
            runtime = update_worker._runtime(request, job=job)
        runtime['mount']()
        self.assertIn('SyntheticSafetyDoctrine', (self.profile / 'SOUL.md').read_text())
        changed = {**request, 'candidate_commit': '0' * 40}
        with patch.object(update_worker, '_check_gateway_launcher', side_effect=AssertionError('Must refuse before systemd')):
            with self.assertRaises(PermissionError):
                update_worker._runtime(changed, job=job)

    def test_update_failure_revokes_authority_and_tampered_jobs_do_not_consume_it(self):
        job = self.profile / 'update-job'
        job.mkdir(mode=0o700)
        request = self.request()
        authorization = self.fixture.issue(binding=self.fixture.admin().job_binding(job, request, 'apply'))
        request['memory_authorization'] = str(authorization)
        (job / 'request.json').write_text(json.dumps({**request, 'candidate_commit': '0' * 40}))
        with self.assertRaises(PermissionError):
            update_worker.run_update_job(job)
        self.assertTrue(authorization.exists())
        (job / 'request.json').write_text(json.dumps(request))
        with patch.object(update_worker, '_execute_update_job', side_effect=RuntimeError('Synthetic interruption')):
            with self.assertRaisesRegex(RuntimeError, 'Synthetic interruption'):
                update_worker.run_update_job(job)
        self.assertFalse(authorization.exists())


if __name__ == '__main__':
    unittest.main()
