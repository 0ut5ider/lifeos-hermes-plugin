# ABOUTME: Exercises installation owner authorization through real Hermes password sessions.
# ABOUTME: Runs native finalization and validates queued update grants without starting systemd services.
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hermes_cli.dashboard_auth.middleware import gated_auth_middleware
from hermes_cli.dashboard_auth.registry import register_global_provider, restore_registration, snapshot_registration
from hermes_cli.dashboard_auth.routes import router as auth_router, _reset_password_rate_limit
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password
import test_memory_admin_install as install_fixture


class MemoryAdminDashboardTests(unittest.TestCase):
    prefix = '/api/plugins/lifeos-hook-bridge/installation'
    account = 'dashboard:basic:synthetic-owner'

    def setUp(self):
        self.fixture = install_fixture.MemoryAdminInstallTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.fixture.configuration
        self.configuration.update(lambda config: config['accounts'].update({self.account: config['principal']}))
        self.environment = patch.dict(os.environ, {'HOME': str(self.fixture.root.parent),
                                                  'HERMES_HOME': str(self.fixture.profile)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        _reset_password_rate_limit()
        self.addCleanup(_reset_password_rate_limit)
        previous = snapshot_registration('basic')
        self.provider = BasicAuthProvider(username='synthetic-owner', password_hash=hash_password('synthetic-password'),
                                          secret=secrets.token_bytes(32))
        register_global_provider(self.provider)
        self.addCleanup(restore_registration, 'basic', self.provider, previous)
        path = Path(__file__).parents[1] / 'lifeos_hook_bridge/dashboard/plugin_api.py'
        spec = importlib.util.spec_from_file_location('administrative_dashboard_test_api', path)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.api.INSTALLED_ROOT = self.fixture.root
        self.api.HERMES_HOME = self.fixture.profile
        self.api.BASELINE_PATH = self.fixture.baseline
        self.api.INSTALL_CANDIDATE = self.fixture.candidate
        self.api.LIFEOS_UPDATE_ROOT = self.fixture.profile / 'state/updates'
        self.api.HOST_SOURCE = install_fixture.HOST
        self.commands = patch.dict(os.environ, {'PATH': str(self.fixture.hermes.parent) + os.pathsep + os.environ['PATH']})
        self.commands.start()
        self.addCleanup(self.commands.stop)
        # The fixture supplies its exact source revision and patch list to the real validators.
        self.api.validate_prepared_lifeos = lambda candidate: self.api.install_module.validate_candidate(
            candidate, self.fixture.revision, self.fixture.patches, ('lifeos-test.patch',))
        self.api.finalize_prepared_lifeos = lambda candidate, installed, profile, baseline, create, save, **options: \
            self.api.install_module.finalize_lifeos(candidate, installed, profile, baseline,
                self.fixture.fixture.fixture.memory.bun, str(self.fixture.hermes), self.fixture.revision,
                self.fixture.patches, ('lifeos-test.patch',), create, save, **options)
        self.app = FastAPI()
        self.app.state.auth_required = True
        self.app.middleware('http')(gated_auth_middleware)
        self.app.include_router(auth_router)
        self.app.include_router(self.api.router, prefix='/api/plugins/lifeos-hook-bridge')
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def login(self):
        response = self.client.post('/auth/password-login', json={'provider': 'basic',
            'username': 'synthetic-owner', 'password': 'synthetic-password'})
        self.assertEqual(response.status_code, 200, response.text)

    def grants(self):
        return list((self.fixture.profile / '.lifeos-memory-admin').glob('*.json'))

    def post(self, path):
        return self.client.post(self.prefix + path)

    def test_verified_owner_finalizes_real_native_mount_and_revokes_grant(self):
        self.login()
        response = self.post('/finalize')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['mounted'])
        self.assertTrue(self.fixture.baseline.exists())
        self.assertIn('SyntheticSafetyDoctrine', (self.fixture.profile / 'SOUL.md').read_text())
        self.assertEqual(self.grants(), [])

    def test_verified_owner_remounts_without_enabling_memory_ownership(self):
        self.login()
        response = self.client.post('/api/plugins/lifeos-hook-bridge/memory/remount')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertIn('SyntheticSafetyDoctrine', (self.fixture.profile / 'SOUL.md').read_text())
        self.assertEqual(self.grants(), [])
        self.assertFalse(self.configuration.load().get('ownership_enabled', False))

    def test_remount_refuses_anonymous_revoked_and_cross_origin_requests(self):
        path = '/api/plugins/lifeos-hook-bridge/memory/remount'
        self.app.state.auth_required = False
        self.assertEqual(self.client.post(path).status_code, 401)
        self.app.state.auth_required = True
        self.login()
        self.assertEqual(self.client.post(path, headers={'Origin':'https://other.invalid'}).status_code, 403)
        self.assertEqual(self.client.post(path + '?home=other').status_code, 400)
        self.assertEqual(self.client.post(path, json={'account':self.account}).status_code, 400)
        self.configuration.update(lambda config:config['accounts'].pop(self.account))
        self.assertEqual(self.client.post(path).status_code, 403)
        self.assertFalse((self.fixture.profile / 'SOUL.md').exists())

    def test_owner_recovers_a_process_killed_mount_through_dashboard(self):
        administration = self.fixture.fixture.admin()
        authorization = administration.issue(self.configuration, self.account)
        self.addCleanup(administration.revoke, self.configuration, authorization)
        environment = administration.mount_environment(self.fixture.root, self.fixture.profile, authorization)
        program = ('import os,signal,sys\nfrom pathlib import Path\n'
            'from lifeos_hook_bridge import mount_transaction as module\n'
            'root,profile,baseline,bun,hermes=sys.argv[1:]\n'
            'publish=module.publish\n'
            'def interrupted(path,data):\n'
            '    publish(path,data)\n'
            '    if path==Path(profile)/"SOUL.md": os.kill(os.getpid(),signal.SIGKILL)\n'
            'module.publish=interrupted\n'
            'module.MountTransaction(root,profile,baseline).execute(dict(os.environ),bun,hermes)\n')
        result = subprocess.run([sys.executable, '-c', program, str(self.fixture.root), str(self.fixture.profile),
            str(self.fixture.baseline), self.fixture.fixture.fixture.memory.bun, str(self.fixture.hermes)],
            env={**environment, 'PYTHONPATH':str(Path(__file__).parents[1])+os.pathsep+str(install_fixture.HOST)},
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
        self.assertEqual(result.stderr, '')
        administration.revoke(self.configuration, authorization)
        self.login()
        self.assertTrue(self.client.get(self.prefix).json()['mount']['recovery_required'])
        response = self.post('/mount/recover')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['state'], 'rolled_back')
        self.assertFalse((self.fixture.profile / 'SOUL.md').exists())
        self.assertEqual(self.grants(), [])

    def test_unconfigured_memory_remount_refuses_before_changing_profile(self):
        self.login()
        self.configuration.path.unlink()
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        response = self.client.post('/api/plugins/lifeos-hook-bridge/memory/remount')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertFalse((self.fixture.profile / 'SOUL.md').exists())

    def test_anonymous_and_fabricated_owner_cannot_authorize_even_with_host_gate_disabled(self):
        self.app.state.auth_required = False
        for path in ('/finalize', '/update', '/update/recover', '/update/restore'):
            with self.subTest(path=path):
                response = self.client.post(self.prefix + path, json={'account': self.account},
                    headers={'X-LifeOS-Owner': 'owner', 'X-Forwarded-User': 'synthetic-owner'})
                self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(self.grants(), [])
        self.assertFalse(self.fixture.baseline.exists())

    def test_revoked_owner_cannot_finalize_or_leave_authorization(self):
        self.login()
        self.configuration.update(lambda config: config['accounts'].pop(self.account))
        response = self.post('/finalize')
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.grants(), [])
        self.assertFalse((self.fixture.profile / 'SOUL.md').exists())

    def prepare_baseline(self):
        self.login()
        response = self.post('/finalize')
        self.assertEqual(response.status_code, 200, response.text)

    def test_update_queue_seals_private_job_with_current_verified_owner(self):
        self.prepare_baseline()
        queued = []
        # Queue acceptance is a component test. It does not claim a live systemd update.
        with patch.object(self.api, '_launch_lifeos_update', side_effect=lambda job: queued.append(job)):
            response = self.post('/update')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(queued), 1)
        job = queued[0]
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration, authorization)
        config, scope = self.fixture.fixture.admin().validate(self.configuration, authorization,
            binding=self.fixture.fixture.admin().job_binding(job, request, 'apply'), check_binding=True)
        self.assertEqual(scope.writer, self.account)
        self.assertEqual((job / 'request.json').stat().st_mode & 0o777, 0o600)
        self.assertNotIn('memory_authorization', response.text)
        self.assertFalse(config.get('ownership_enabled', False))

    def test_queue_launch_failure_revokes_grant_and_removes_job(self):
        self.prepare_baseline()
        with patch.object(self.api, '_launch_lifeos_update', side_effect=RuntimeError('Synthetic launch failure')):
            response = self.post('/update')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.grants(), [])
        self.assertEqual(list(self.api.LIFEOS_UPDATE_ROOT.iterdir()), [])

    def test_revoked_owner_cannot_queue_an_update(self):
        self.prepare_baseline()
        self.configuration.update(lambda config: config['accounts'].pop(self.account))
        with patch.object(self.api, '_launch_lifeos_update', side_effect=AssertionError('Owner must be checked first')):
            response = self.post('/update')
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.grants(), [])
        self.assertEqual(list(self.api.LIFEOS_UPDATE_ROOT.iterdir()), [])

    def interrupted_job(self):
        job = self.api.LIFEOS_UPDATE_ROOT / 'interrupted-synthetic-job'
        job.mkdir(parents=True, mode=0o700)
        request = self.fixture.request()
        authorization = self.fixture.fixture.admin().issue(self.configuration, self.account,
            binding=self.fixture.fixture.admin().job_binding(job, request, 'apply'))
        request['memory_authorization'] = str(authorization)
        (job / 'request.json').write_text(json.dumps(request) + '\n')
        (job / 'request.json').chmod(0o600)
        (job / 'status.json').write_text(json.dumps({'state': 'interrupted', 'unit': 'synthetic-unit'}) + '\n')
        (job / 'status.json').chmod(0o600)
        (job / 'snapshot').mkdir()
        (job / 'snapshot/manifest.json').write_text(json.dumps({'state': 'swapped'}))
        self.fixture.fixture.admin().revoke(self.configuration, authorization)
        return job

    def test_recovery_requires_fresh_action_bound_owner_authorization(self):
        self.login()
        job = self.interrupted_job()
        with patch.object(self.api, '_launch_lifeos_update') as launched:
            response = self.post('/update/recover')
        self.assertEqual(response.status_code, 200, response.text)
        launched.assert_called_once_with(job, 'recover')
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration, authorization)
        self.fixture.fixture.admin().validate(self.configuration, authorization,
            binding=self.fixture.fixture.admin().job_binding(job, request, 'recover'), check_binding=True, purpose='recover')
        with self.assertRaises(PermissionError):
            self.fixture.fixture.admin().validate(self.configuration, authorization,
                binding=self.fixture.fixture.admin().job_binding(job, request, 'apply'), check_binding=True)

    def applied_job(self):
        job = self.interrupted_job()
        (job / 'status.json').write_text(json.dumps({'state': 'applied'}) + '\n')
        (job / 'snapshot/manifest.json').write_text(json.dumps({'state': 'applied'}))
        return job

    def test_restore_requires_fresh_action_bound_owner_authorization(self):
        self.login()
        job = self.applied_job()
        with patch.object(self.api, '_launch_lifeos_update') as launched:
            response = self.post('/update/restore')
        self.assertEqual(response.status_code, 200, response.text)
        launched.assert_called_once_with(job, 'restore')
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration, authorization)
        self.fixture.fixture.admin().validate(self.configuration, authorization,
            binding=self.fixture.fixture.admin().job_binding(job, request, 'restore'), check_binding=True)
        with self.assertRaises(PermissionError):
            self.fixture.fixture.admin().validate(self.configuration, authorization,
                binding=self.fixture.fixture.admin().job_binding(job, request, 'apply'), check_binding=True)

    def test_failed_restore_launch_preserves_retryable_job_state(self):
        self.login()
        job = self.applied_job()
        before_request = (job / 'request.json').read_bytes()
        before_status = (job / 'status.json').read_bytes()
        with patch.object(self.api, '_launch_lifeos_update', side_effect=RuntimeError('Synthetic launch failure')):
            response = self.post('/update/restore')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.grants(), [])
        self.assertEqual((job / 'request.json').read_bytes(), before_request)
        self.assertEqual((job / 'status.json').read_bytes(), before_status)

    def test_revoked_owner_cannot_restore_update(self):
        self.login()
        self.applied_job()
        self.configuration.update(lambda config: config['accounts'].pop(self.account))
        with patch.object(self.api, '_launch_lifeos_update', side_effect=AssertionError('Owner must be checked first')):
            response = self.post('/update/restore')
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.grants(), [])

    def test_restore_refuses_an_unapplied_update(self):
        self.login()
        self.interrupted_job()
        with patch.object(self.api, '_launch_lifeos_update', side_effect=AssertionError('State must be checked first')):
            response = self.post('/update/restore')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.grants(), [])

    def test_restore_refuses_cross_origin_and_request_overrides(self):
        self.login()
        self.applied_job()
        path = self.prefix + '/update/restore'
        with patch.object(self.api, '_launch_lifeos_update', side_effect=AssertionError('Admission must run first')):
            self.assertEqual(self.client.post(path, headers={'Origin': 'https://other.invalid'}).status_code, 403)
            self.assertEqual(self.client.post(path + '?job=other').status_code, 400)
            self.assertEqual(self.client.post(path, json={'job': 'other'}).status_code, 400)
        self.assertEqual(self.grants(), [])

    def test_restore_refuses_a_job_for_another_installation(self):
        self.login()
        job = self.applied_job()
        request = json.loads((job / 'request.json').read_text())
        request['hermes_home'] = str(self.fixture.profile.parent / 'other-profile')
        (job / 'request.json').write_text(json.dumps(request))
        with patch.object(self.api, '_launch_lifeos_update', side_effect=AssertionError('Binding must run first')):
            response = self.post('/update/restore')
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.grants(), [])

    def test_failed_recovery_launch_preserves_retryable_job_state(self):
        self.login()
        job = self.interrupted_job()
        before_request = (job / 'request.json').read_bytes()
        before_status = (job / 'status.json').read_bytes()
        with patch.object(self.api, '_launch_lifeos_update', side_effect=RuntimeError('Synthetic launch failure')):
            response = self.post('/update/recover')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.grants(), [])
        self.assertEqual((job / 'request.json').read_bytes(), before_request)
        self.assertEqual((job / 'status.json').read_bytes(), before_status)

    def test_revoked_owner_cannot_reauthorize_recovery(self):
        self.login()
        job = self.interrupted_job()
        before_request = (job / 'request.json').read_bytes()
        before_status = (job / 'status.json').read_bytes()
        self.configuration.update(lambda config: config['accounts'].pop(self.account))
        with patch.object(self.api, '_launch_lifeos_update', side_effect=AssertionError('Owner must be checked first')):
            response = self.post('/update/recover')
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.grants(), [])
        self.assertEqual((job / 'request.json').read_bytes(), before_request)
        self.assertEqual((job / 'status.json').read_bytes(), before_status)

    def test_recovery_authorizes_a_missing_install_directory_without_prompt_access(self):
        self.login()
        job = self.interrupted_job()
        prior = job / 'snapshot/live-prior'
        self.fixture.root.rename(prior)
        with patch.object(self.api, '_launch_lifeos_update') as launched:
            response = self.post('/update/recover')
        self.assertEqual(response.status_code, 200, response.text)
        launched.assert_called_once_with(job, 'recover')
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration, authorization)
        self.assertEqual(json.loads(authorization.read_text())['payload']['purpose'], 'recover')
        # Restoring the source directory does not convert recovery authority into mount authority.
        prior.rename(self.fixture.root)
        from lifeos_hook_bridge.memory_service import MemoryService
        self.assertFalse(MemoryService(self.configuration).administrative(
            authorization, 'prompt_bundle', {'keepOutputFormat': False})['ok'])


if __name__ == '__main__':
    unittest.main()
