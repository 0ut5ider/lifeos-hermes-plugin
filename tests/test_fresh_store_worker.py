# ABOUTME: Verifies detached fresh-store preparation, failure reporting, interruption, and removal.
# ABOUTME: Runs the actual worker program in a separate process against the native candidate when available.
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from test_fresh_store_status import FreshStoreStatusTests

WORKER = Path(__file__).parents[1] / 'lifeos_hook_bridge/fresh_store_worker.py'
CANDIDATE = os.environ.get('LIFEOS_FRESH_SOURCE', '')


def descendants(root):
    children = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                parent = int((entry / 'stat').read_text().rsplit(')', 1)[1].split()[1])
            except (OSError, IndexError, ValueError):
                continue
            children.setdefault(parent, []).append(int(entry.name))
    found, pending = [], [root]
    while pending:
        for child in children.get(pending.pop(), []):
            found.append(child)
            pending.append(child)
    return found


class FreshStoreWorkerTests(FreshStoreStatusTests):
    def start(self, candidate, identifier='a' * 32, principal='Adrian'):
        environment = {**os.environ, 'HOME': str(self.fixture.fixture.home)}
        return subprocess.Popen([sys.executable, str(WORKER), '--configuration', str(self.fixture.configuration.path),
                                 '--candidate', str(candidate), '--identifier', identifier,
                                 '--principal-name', principal, '--assistant-name', 'Cerebo',
                                 '--account', 'dashboard:owner'], env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)

    def row(self, identifier='a' * 32):
        return next(row for row in self.status()['stores'] if row['identifier'] == identifier)

    def test_failed_preparation_is_reported_with_its_names_and_a_reason(self):
        process = self.start(self.fixture.fixture.home / 'missing-candidate')
        self.assertNotEqual(process.wait(timeout=60), 0)
        self.assertEqual(self.row(), {'identifier': 'a' * 32, 'state': 'failed',
                                      'names': {'principal': 'Adrian', 'assistant': 'Cerebo'},
                                      'reason': 'Fresh store preparation requires a verified native candidate'})

    def test_invalid_names_or_identifier_create_no_store(self):
        for identifier, principal in (('a' * 32, '<script>'), ('../outside', 'Adrian')):
            with self.subTest(identifier=identifier):
                process = self.start(self.fixture.fixture.home / 'missing-candidate', identifier, principal)
                self.assertNotEqual(process.wait(timeout=60), 0)
                self.assertEqual(self.status()['stores'], [])

    def test_removal_deletes_an_interrupted_or_failed_store_and_keeps_others(self):
        self.store('d' * 32, 'preparing')
        self.store('f' * 32, 'review')
        result = self.operation().remove('d' * 32, account='dashboard:owner')
        self.assertEqual(result, {'identifier': 'd' * 32, 'removed': True})
        self.assertFalse((self.base / ('d' * 32)).exists())
        self.assertEqual([row['identifier'] for row in self.status()['stores']], ['f' * 32])

    def test_removal_refuses_a_running_preparation_an_unknown_name_and_other_owners(self):
        from lifeos_hook_bridge.installation_lock import installation_lock
        self.store('d' * 32, 'preparing')
        with installation_lock(self.profile):
            with self.assertRaises(MemoryUnavailable):
                self.operation().remove('d' * 32, account='dashboard:owner')
        for identifier in ('../d', 'e' * 32, 'd' * 31):
            with self.subTest(identifier=identifier):
                with self.assertRaises((MemoryUnavailable, ValueError)):
                    self.operation().remove(identifier, account='dashboard:owner')
        with self.assertRaises(PermissionError):
            self.operation().remove('d' * 32, account='dashboard:guest')
        self.assertTrue((self.base / ('d' * 32)).is_dir())

    @unittest.skipUnless(CANDIDATE and shutil.which('bun'), 'The complete native candidate and Bun are required')
    def test_detached_preparation_survives_its_launcher_and_reaches_review(self):
        process = self.start(CANDIDATE)
        self.assertEqual(process.wait(timeout=900), 0, process.stderr.read())
        row = self.row()
        self.assertEqual((row['state'], row['names'], row['active_facts']),
                         ('review', {'principal': 'Adrian', 'assistant': 'Cerebo'}, 0))

    @unittest.skipUnless(CANDIDATE and shutil.which('bun'), 'The complete native candidate and Bun are required')
    def test_killed_preparation_is_interrupted_and_can_be_removed(self):
        process = self.start(CANDIDATE)
        deadline = time.time() + 120
        while not (self.base / ('a' * 32) / 'review.json').exists() and time.time() < deadline:
            time.sleep(0.2)
        time.sleep(2)
        # A stopped systemd unit ends every process in its control group, including installer
        # children that start their own sessions. The test ends the complete process tree the same way.
        for pid in [process.pid, *descendants(process.pid)]:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=30)
        self.assertEqual(self.row()['state'], 'interrupted')
        self.operation().remove('a' * 32, account='dashboard:owner')
        self.assertEqual(self.status()['stores'], [])


class FreshStoreWorkerRouteTests(unittest.TestCase):
    def test_owner_starts_a_detached_preparation_and_removes_its_failed_store(self):
        import importlib.util
        from unittest.mock import patch
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from test_memory_dashboard import owner_client
        fixture = FreshStoreWorkerTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        path = Path(__file__).parents[1] / 'lifeos_hook_bridge/dashboard/plugin_api.py'
        launched = []
        with patch.dict(os.environ, {'HOME': str(fixture.fixture.fixture.home), 'HERMES_HOME': str(fixture.profile)}):
            spec = importlib.util.spec_from_file_location('fresh_store_worker_http', path)
            api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
            api.INSTALL_CANDIDATE = fixture.fixture.fixture.home / 'missing-candidate'

            def launch(arguments, unit):
                launched.append(unit)
                subprocess.run([sys.executable, str(WORKER), *arguments], env={**os.environ, 'HOME': str(fixture.fixture.fixture.home)},
                               capture_output=True, timeout=120)
            api._launch_fresh_store = launch
            app = FastAPI(); app.include_router(api.router, prefix='/api/plugins/lifeos-hook-bridge')
            api.install_memory_cache_headers(app)
            base = '/api/plugins/lifeos-hook-bridge/memory/fresh'
            body = {'principal_name': 'Adrian', 'assistant_name': 'Cerebo'}
            with owner_client(app, fixture.profile) as client:
                with TestClient(app) as guest:
                    self.assertEqual(guest.post(base + '/start', json=body).status_code, 401)
                for extra in ('candidate', 'identifier', 'account'):
                    response = client.post(base + '/start', json=body | {extra: 'x'})
                    self.assertEqual(response.status_code, 400, response.text)
                response = client.post(base + '/start', json=body)
                self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(response.headers['cache-control'], 'no-store')
                identifier = response.json()['identifier']
                self.assertEqual(launched, ['lifeos-fresh-store-' + identifier])
                stores = client.get(base + '/status').json()['stores']
                self.assertEqual([(row['identifier'], row['state']) for row in stores], [(identifier, 'failed')])
                self.assertEqual(client.delete(base + '/stores/' + 'b' * 32).status_code, 409)
                response = client.delete(base + '/stores/' + identifier)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(client.get(base + '/status').json()['stores'], [])
                fixture.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
                self.assertEqual(client.post(base + '/start', json=body).status_code, 403)
