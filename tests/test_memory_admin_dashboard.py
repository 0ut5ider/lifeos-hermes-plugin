# ABOUTME: Exercises installation owner authorization through real Hermes password sessions.
# ABOUTME: Runs native finalization and validates queued update grants without starting systemd services.
import importlib.util
import contextlib
from concurrent.futures import ThreadPoolExecutor
import io
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
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

    def test_first_dashboard_account_claims_an_unconfigured_installation(self):
        self.login()
        self.configuration.path.unlink()
        claim = '/api/plugins/lifeos-hook-bridge/memory/owner'
        self.assertEqual(self.client.post(claim, headers={'Origin': 'https://other.invalid'}).status_code, 403)
        self.assertFalse(self.configuration.path.exists())
        response = self.client.post(claim)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['state'], 'prepared')
        config = self.configuration.load()
        self.assertEqual(config['root'], str(self.fixture.root.absolute()))
        self.assertEqual(config['accounts'], {self.account: config['principal']})
        self.assertIs(config['ownership_enabled'], False)
        self.assertIs(config['sharing_enabled'], False)
        self.assertEqual(self.configuration.path.stat().st_mode & 0o777, 0o600)
        second = self.client.post(claim)
        self.assertEqual(second.status_code, 409, second.text)
        self.assertEqual(self.configuration.load(), config)

    def test_owner_claim_requires_a_session_and_an_installed_lifeos(self):
        self.configuration.path.unlink()
        claim = '/api/plugins/lifeos-hook-bridge/memory/owner'
        self.assertEqual(self.client.post(claim).status_code, 401)
        self.login()
        (self.fixture.root / 'LIFEOS/VERSION').unlink()
        self.assertEqual(self.client.post(claim).status_code, 409)
        self.assertFalse(self.configuration.path.exists())

    def review_store(self, source):
        from lifeos_hook_bridge.fresh_store import FreshStore
        store = FreshStore(self.configuration)
        folder = store._ensure_base() / ('a' * 32)
        (folder / 'home/.claude/LIFEOS').mkdir(parents=True)
        os.chmod(folder, 0o700)
        document = {'version': 1, 'state': 'review', 'profile': str(self.fixture.profile.absolute()),
                    'names': {'principal': 'Adrian', 'assistant': 'Cerebo'}, 'source': source,
                    'active_facts': 0, 'activation_ready': False,
                    'retained_installation': str(self.fixture.root)}
        document['signature'] = hashlib.sha256((json.dumps(document, sort_keys=True, indent=2) + '\n').encode()).hexdigest()
        (folder / 'review.json').write_text(json.dumps(document, sort_keys=True, indent=2) + '\n')
        os.chmod(folder / 'review.json', 0o600)
        return folder

    def test_owner_queues_selection_of_a_reviewed_store_and_return(self):
        self.login()
        source = self.api.validate_prepared_lifeos(self.api._candidate_path())
        folder = self.review_store(source)
        self.api.SELECTION_ROOT = self.fixture.profile / 'state/selections'
        path = '/api/plugins/lifeos-hook-bridge/installation/selection'
        self.assertEqual(self.client.post(path, json={'store': 'b' * 32}).status_code, 409)
        self.assertEqual(self.client.post(path, json={'store': 'a' * 32, 'home': '/'}).status_code, 400)
        self.assertEqual(self.client.post(path, json={'store': 'a' * 32},
                                          headers={'Origin': 'https://other.invalid'}).status_code, 403)
        self.assertEqual(self.client.post(path + '/return').status_code, 409)
        with patch.object(self.api, '_launch_selection') as launched:
            response = self.client.post(path, json={'store': 'a' * 32})
        self.assertEqual(response.status_code, 200, response.text)
        job = Path(response.json()['job'])
        launched.assert_called_once_with(job, 'select')
        request = json.loads((job / 'request.json').read_text())
        self.assertEqual(request['target_home'], str(folder / 'home'))
        self.assertEqual(request['profile'], str(self.fixture.profile))
        self.assertEqual((job / 'request.json').stat().st_mode & 0o777, 0o600)

    def test_fresh_store_preparation_uses_the_selected_candidate(self):
        self.login()
        selected = self.fixture.candidate.with_name(self.fixture.candidate.name + '-' + 'c' * 32)
        marker = self.fixture.candidate.with_name(self.fixture.candidate.name + '.selected.json')
        marker.write_text(json.dumps({'name': selected.name}))
        with patch.object(self.api, '_launch_fresh_store') as launched:
            response = self.client.post('/api/plugins/lifeos-hook-bridge/memory/fresh/start',
                                        json={'principal_name': 'Adrian', 'assistant_name': 'Cerebo'})
        self.assertEqual(response.status_code, 202, response.text)
        arguments = launched.call_args.args[0]
        self.assertEqual(arguments[arguments.index('--candidate') + 1], str(selected))

    def test_selection_refuses_a_store_from_another_candidate(self):
        self.login()
        source = dict(self.api.validate_prepared_lifeos(self.api._candidate_path()), upstream_commit='0' * 40)
        self.review_store(source)
        self.api.SELECTION_ROOT = self.fixture.profile / 'state/selections'
        with patch.object(self.api, '_launch_selection', side_effect=AssertionError('must refuse first')):
            response = self.client.post('/api/plugins/lifeos-hook-bridge/installation/selection',
                                        json={'store': 'a' * 32})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn('another LifeOS candidate', response.text)

    def test_verified_owner_finalizes_real_native_mount_and_revokes_grant(self):
        self.login()
        response = self.post('/finalize')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['mounted'])
        self.assertTrue(self.fixture.baseline.exists())
        self.assertIn('SyntheticSafetyDoctrine', (self.fixture.profile / 'SOUL.md').read_text())
        self.assertEqual(self.grants(), [])

    def test_installation_actions_refuse_cross_origin_and_request_overrides(self):
        self.login()
        for action in ('finalize', 'update', 'prepare', 'apply', 'prepare-hermes', 'apply-hermes', 'restore-hermes'):
            url = self.prefix + '/' + action
            for endpoint, options, expected in (
                    (url, {'headers': {'Origin': 'http://testserver:8081'}}, 403),
                    (url + '?installed=other', {}, 400),
                    (url, {'json': {'installed': 'other'}}, 400)):
                with self.subTest(action=action, request=options or endpoint):
                    response = self.client.post(endpoint, **options)
                    self.assertEqual(response.status_code, expected, response.text)
                    self.assertFalse(self.fixture.baseline.exists())
                    self.assertEqual(self.grants(), [])

    def test_other_mutations_refuse_cross_origin_before_payload_validation(self):
        self.login()
        for method, path in (('POST', '/memory/sharing'), ('PUT', '/settings'),
                             ('POST', '/version-drift'), ('DELETE', '/memory/connections/synthetic')):
            with self.subTest(method=method, path=path):
                response = self.client.request(method, '/api/plugins/lifeos-hook-bridge' + path,
                    headers={'Origin': 'http://testserver:8081'}, json={})
                self.assertEqual(response.status_code, 403, response.text)

    def test_concurrent_updates_cannot_both_admit_a_job(self):
        self.prepare_baseline()
        entered, release = threading.Event(), threading.Event()
        original_status = self.api.get_lifeos_update_status

        def status():
            result = original_status()
            if not entered.is_set():
                entered.set()
                release.wait(timeout=5)
            return result

        with patch.object(self.api, 'get_lifeos_update_status', side_effect=status), \
                patch.object(self.api, '_launch_lifeos_update') as launched, ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(self.post, '/update')
            try:
                self.assertTrue(entered.wait(timeout=5))
                second = self.post('/update')
                self.assertEqual(second.status_code, 409, second.text)
            finally:
                release.set()
                result = first.result(timeout=10)
                self.assertEqual(result.status_code, 200, result.text)
                for grant in self.grants():
                    self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration, grant)
            self.assertEqual(launched.call_count, 1)
            self.assertEqual(len(list(self.api.LIFEOS_UPDATE_ROOT.glob('update-*'))), 1)

    def test_shared_lock_refuses_update_mount_and_host_patch_actions(self):
        self.login()
        from lifeos_hook_bridge.installation_lock import installation_lock
        with installation_lock(self.fixture.profile):
            for path in ('/finalize', '/update', '/update/restore', '/update/recover',
                         '/mount/recover', '/apply-hermes', '/restore-hermes'):
                with self.subTest(path=path):
                    response = self.post(path)
                    self.assertEqual(response.status_code, 409, response.text)
                    self.assertIn('Another installation operation', response.text)
                    self.assertEqual(self.grants(), [])
            response = self.client.post('/api/plugins/lifeos-hook-bridge/memory/remount')
            self.assertEqual(response.status_code, 409, response.text)
        self.assertFalse(self.fixture.baseline.exists())

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

    def test_restore_worker_failure_keeps_authenticated_recovery_available(self):
        from lifeos_hook_bridge import update_worker
        self.login()
        job = self.interrupted_job()
        (job / 'snapshot/manifest.json').write_text(json.dumps({'state': 'restoring'}))
        output = io.StringIO()
        with patch.object(sys, 'argv', ['worker', str(job), '--action', 'restore']), \
                patch.object(update_worker, 'run_update_job', side_effect=RuntimeError('Synthetic restore failure')), \
                contextlib.redirect_stderr(output):
            self.assertEqual(update_worker._main(), 1)
        self.assertIn('Synthetic restore failure', output.getvalue())
        self.assertEqual(self.api.get_lifeos_update_status()['state'], 'interrupted')
        with patch.object(self.api, '_launch_lifeos_update') as launched:
            response = self.post('/update/recover')
        self.assertEqual(response.status_code, 200, response.text)
        launched.assert_called_once_with(job, 'recover')
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration, authorization)
        self.fixture.fixture.admin().validate(self.configuration, authorization,
            binding=self.fixture.fixture.admin().job_binding(job, request, 'recover'), check_binding=True, purpose='recover')

    def test_dead_restore_stop_worker_can_queue_authenticated_recovery(self):
        self.login()
        job = self.interrupted_job()
        (job / 'status.json').write_text(json.dumps({'state': 'restoring', 'unit': 'synthetic-dead-worker'}))
        (job / 'snapshot/manifest.json').write_text(json.dumps({'state': 'restore_stopping'}))
        with patch.object(self.api.subprocess, 'run', return_value=subprocess.CompletedProcess([], 3, '', '')):
            self.assertEqual(self.api.get_lifeos_update_status()['state'], 'interrupted')
            with patch.object(self.api, '_launch_lifeos_update') as launched:
                response = self.post('/update/recover')
        self.assertEqual(response.status_code, 200, response.text)
        launched.assert_called_once_with(job, 'recover')
        request = json.loads((job / 'request.json').read_text())
        authorization = Path(request['memory_authorization'])
        self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration, authorization)
        self.fixture.fixture.admin().validate(self.configuration, authorization,
            binding=self.fixture.fixture.admin().job_binding(job, request, 'recover'), check_binding=True, purpose='recover')

    def test_dead_recovery_worker_reports_its_durable_completed_state(self):
        job = self.interrupted_job()
        for state in ('applied', 'rolled_back'):
            with self.subTest(state=state):
                (job / 'status.json').write_text(json.dumps({'state': 'recovering', 'unit': 'synthetic-dead-worker'}))
                (job / 'snapshot/manifest.json').write_text(json.dumps({'state': state}))
                with patch.object(self.api.subprocess, 'run', return_value=subprocess.CompletedProcess([], 3, '', '')):
                    self.assertEqual(self.api.get_lifeos_update_status()['state'], state)

    def applied_job(self):
        job = self.interrupted_job()
        (job / 'status.json').write_text(json.dumps({'state': 'applied'}) + '\n')
        transaction = self.api.install_module.memory_module('update_transaction')
        shutil.copytree(self.fixture.root, job / 'snapshot/live-prior', symlinks=True)
        bindings = transaction._external_user_data(self.fixture.root, excluded=(job / 'snapshot',))
        (job / 'snapshot/manifest.json').write_text(json.dumps({'state': 'applied',
            'installed': str(self.fixture.root), 'hermes_home': str(self.fixture.profile),
            'mount_state': transaction._mount_state(self.fixture.profile),
            'user_data_links': bindings,
            'user_data': transaction._memory_digest(self.fixture.root, bindings)}))
        return job

    def test_changed_profile_refuses_restore_without_changing_job(self):
        self.login()
        job = self.applied_job()
        before_request = (job / 'request.json').read_bytes()
        before_status = (job / 'status.json').read_bytes()
        target = self.fixture.profile / 'config.yaml'
        target.write_text('Synthetic later model selection\n')
        with patch.object(self.api, '_launch_lifeos_update', side_effect=AssertionError('Profile must be checked first')):
            response = self.post('/update/restore')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn('Hermes profile changed', response.text)
        self.assertEqual(self.grants(), [])
        self.assertEqual((job / 'request.json').read_bytes(), before_request)
        self.assertEqual((job / 'status.json').read_bytes(), before_status)
        self.assertEqual(target.read_text(), 'Synthetic later model selection\n')

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

    def test_recovery_refuses_cross_origin_and_request_overrides(self):
        self.login()
        job = self.interrupted_job()
        before_request = (job / 'request.json').read_bytes()
        before_status = (job / 'status.json').read_bytes()
        path = self.prefix + '/update/recover'
        requests = (
            (path, {'headers': {'Origin': 'https://other.invalid'}}, 403),
            (path + '?job=other', {}, 400),
            (path, {'json': {'job': 'other'}}, 400),
        )
        with patch.object(self.api, '_launch_lifeos_update', side_effect=RuntimeError('Synthetic launch prevented')) as launched:
            for url, options, expected in requests:
                with self.subTest(request=options or url):
                    self.assertEqual(self.client.post(url, **options).status_code, expected)
                    self.assertEqual((job / 'request.json').read_bytes(), before_request)
                    self.assertEqual((job / 'status.json').read_bytes(), before_status)
                    self.assertEqual(self.grants(), [])
            launched.assert_not_called()

    def test_dashboard_remains_responsive_while_recovery_launch_waits(self):
        self.login()
        job = self.interrupted_job()
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()

        @self.app.get('/auth/login/recovery-scheduling-probe')
        async def probe():
            return {'launch_finished': finished.is_set()}

        def launch(selected, action):
            self.assertEqual((selected, action), (job, 'recover'))
            entered.set()
            release.wait(timeout=5)
            finished.set()

        with patch.object(self.api, '_launch_lifeos_update', side_effect=launch), ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.post, '/update/recover')
            try:
                self.assertTrue(entered.wait(timeout=5), 'Recovery did not reach launch')
                response = self.client.get('/auth/login/recovery-scheduling-probe')
                self.assertEqual(response.status_code, 200, response.text)
                self.assertFalse(response.json()['launch_finished'], 'Recovery launch blocked other dashboard requests')
            finally:
                release.set()
                recovery = pending.result(timeout=10)
                self.assertEqual(recovery.status_code, 200, recovery.text)
                request = json.loads((job / 'request.json').read_text())
                self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration,
                                Path(request['memory_authorization']))

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

    def test_dashboard_remains_responsive_while_restore_launch_waits(self):
        self.login()
        job = self.applied_job()
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()

        @self.app.get('/auth/login/restore-scheduling-probe')
        async def probe():
            return {'launch_finished': finished.is_set()}

        def launch(selected, action):
            self.assertEqual((selected, action), (job, 'restore'))
            entered.set()
            release.wait(timeout=2)
            finished.set()

        with patch.object(self.api, '_launch_lifeos_update', side_effect=launch), ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.post, '/update/restore')
            try:
                self.assertTrue(entered.wait(timeout=5), 'Restore did not reach launch')
                response = self.client.get('/auth/login/restore-scheduling-probe')
                self.assertEqual(response.status_code, 200, response.text)
                self.assertFalse(response.json()['launch_finished'], 'Restore launch blocked other dashboard requests')
            finally:
                release.set()
                result = pending.result(timeout=10)
                self.assertEqual(result.status_code, 200, result.text)
                request = json.loads((job / 'request.json').read_text())
                self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration,
                                Path(request['memory_authorization']))

    def test_changed_embedded_user_data_does_not_block_restore(self):
        self.login()
        job = self.applied_job()
        (self.fixture.root / 'USER.md').write_text('Synthetic later user edit')
        with patch.object(self.api, '_launch_lifeos_update') as launched:
            response = self.post('/update/restore')
        self.assertEqual(response.status_code, 200, response.text)
        launched.assert_called_once_with(job, 'restore')
        self.assertEqual(json.loads((job / 'status.json').read_text())['state'], 'restoring')
        request = json.loads((job / 'request.json').read_text())
        self.addCleanup(self.fixture.fixture.admin().revoke, self.configuration,
                        Path(request['memory_authorization']))

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
