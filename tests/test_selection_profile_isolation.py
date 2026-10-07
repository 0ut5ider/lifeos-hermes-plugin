# ABOUTME: Exercises selection status and recovery across profiles with different owner bindings.
# ABOUTME: Records real dashboard launch commands through a local transport without starting services.
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from starlette.requests import Request
from lifeos_hook_bridge.memory_service import MemoryConfiguration


class SelectionProfileIsolationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / 'account'
        self.a = self.home / '.hermes/profiles/a'
        self.b = self.home / '.hermes/profiles/b'
        self.owner_a, self.owner_b = 'dashboard:basic:owner-a', 'dashboard:basic:owner-b'
        for profile, owner in ((self.a, self.owner_a), (self.b, self.owner_b)):
            profile.mkdir(parents=True, mode=0o700)
            MemoryConfiguration(profile / 'lifeos-memory.json').save({'version': 1,
                'root': str(self.home / '.claude'), 'principal': 'owner', 'accounts': {owner: 'owner'},
                'destinations': {}, 'clients': {}})
        (self.home / '.claude/LIFEOS').mkdir(parents=True)
        self.recorder = self.home / 'launch.json'
        binaries = self.home / 'bin'
        binaries.mkdir()
        launcher = binaries / 'systemd-run'
        launcher.write_text('#!' + sys.executable + '\nimport json,sys\nfrom pathlib import Path\n'
                            f'Path({str(self.recorder)!r}).write_text(json.dumps(sys.argv[1:]))\n')
        launcher.chmod(0o700)
        (binaries / 'systemctl').write_bytes(launcher.read_bytes())
        (binaries / 'systemctl').chmod(0o700)
        environment = patch.dict(os.environ, {'HOME': str(self.home), 'HERMES_HOME': str(self.b),
            'PATH': str(binaries) + os.pathsep + os.environ['PATH']})
        environment.start()
        self.addCleanup(environment.stop)
        path = Path(__file__).parents[1] / 'lifeos_hook_bridge/dashboard/plugin_api.py'
        spec = importlib.util.spec_from_file_location('selection_profile_isolation_api', path)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)

    def job(self, profile, name, state='interrupted', *, journal=True):
        job = self.api.SELECTION_ROOT / name
        job.mkdir(parents=True, mode=0o700)
        (job / 'request.json').write_text(json.dumps({'profile': str(profile), 'target_home': None,
            'candidate': None, 'hermes_command': '/synthetic/hermes'}))
        (job / 'status.json').write_text(json.dumps({'state': state}))
        if journal:
            (job / 'transaction').mkdir()
            (job / 'transaction/journal.json').write_text(json.dumps({'version': 1, 'profile': str(profile),
                'state': 'published', 'previous': {'home': str(self.home), 'setting': None, 'configured': False,
                    'root': str(self.home / '.claude')},
                'target': {'home': None, 'workspace': str(self.home / 'HermesWorkspace')}}))
        return job

    def recover(self):
        async def receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        request = Request({'type': 'http', 'method': 'POST', 'scheme': 'http', 'server': ('testserver', 80),
            'path': '/installation/selection/recover', 'query_string': b'', 'headers': []}, receive=receive)
        return asyncio.run(self.api.recover_installation_selection(request, account=self.owner_b))

    def test_status_does_not_show_another_profiles_interrupted_job(self):
        self.job(self.a, 'selection-a')
        result = self.api.get_installation_selection(account=self.owner_b)
        self.assertEqual(result['job'], {'state': 'none'})

    def test_latest_selection_belongs_to_the_current_profile(self):
        own = self.job(self.b, 'selection-b')
        other = self.job(self.a, 'selection-a')
        os.utime(own, ns=(1, 1))
        os.utime(other, ns=(2, 2))
        self.assertEqual(self.api._latest_selection(), own)

    def test_recovery_refuses_another_profiles_job_before_launch(self):
        other = self.job(self.a, 'selection-a')
        with self.assertRaises(self.api.HTTPException) as raised:
            self.recover()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertFalse(self.recorder.exists())
        self.assertEqual(json.loads((other / 'status.json').read_text())['state'], 'interrupted')

    def test_own_recovery_passes_the_verified_account_and_profile_to_the_worker(self):
        own = self.job(self.b, 'selection-b')
        self.assertEqual(self.recover()['job'], str(own))
        command = json.loads(self.recorder.read_text())
        self.assertEqual(command[command.index('--account') + 1], self.owner_b)
        self.assertIn(f'--setenv=HERMES_HOME={self.b}', command)
        self.assertIn(str(own), command)

    def test_launch_rechecks_the_job_profile_before_publishing_status(self):
        other = self.job(self.a, 'selection-a')
        module = self.api.install_module.memory_module('installation_selection')
        with self.assertRaisesRegex(module.SelectionError, 'another Hermes profile'):
            self.api._launch_selection(other, 'recover', self.owner_b)
        self.assertFalse(self.recorder.exists())
        self.assertEqual(json.loads((other / 'status.json').read_text())['state'], 'interrupted')

    def test_worker_refuses_another_profile_and_preserves_job_status(self):
        other = self.job(self.a, 'selection-a')
        self.worker_refuses(other, 'another Hermes profile')

    def test_worker_rechecks_a_revoked_owner_before_service_access(self):
        own = self.job(self.b, 'selection-b')
        configuration = MemoryConfiguration(self.b / 'lifeos-memory.json')
        configuration.update(lambda config: config['accounts'].clear())
        self.worker_refuses(own, 'no installation owner binding')

    def test_worker_refuses_a_journal_bound_to_another_profile(self):
        own = self.job(self.b, 'selection-b')
        (own / 'transaction/journal.json').write_text(json.dumps({'profile': str(self.a)}))
        self.worker_refuses(own, 'journal belongs to another Hermes profile')

    def worker_refuses(self, job, message):
        status = (job / 'status.json').read_bytes()
        worker = Path(__file__).parents[1] / 'lifeos_hook_bridge/selection_worker.py'
        result = subprocess.run([sys.executable, str(worker), str(job), '--action', 'recover',
                                 '--account', self.owner_b], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertIn(message, result.stderr)
        self.assertFalse(self.recorder.exists(), 'The refused worker must not access services')
        self.assertEqual((job / 'status.json').read_bytes(), status)

    def test_pending_jobs_still_serialize_shared_account_services(self):
        self.job(self.a, 'selection-a')
        with self.assertRaises(self.api.HTTPException) as raised:
            self.api._queue_selection(self.owner_b, None)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn('profile owner', raised.exception.detail)
        self.assertEqual(self.api._selection_status(), {'state': 'none'})

    def test_invalid_requests_and_profile_aliases_cannot_select_a_job(self):
        job = self.job(self.b, 'selection-b')
        for document in ('null', '{', json.dumps({'profile': str(self.b / '..' / 'b')})):
            with self.subTest(document=document):
                (job / 'request.json').write_text(document)
                self.assertIsNone(self.api._latest_selection())


if __name__ == '__main__':
    unittest.main()
