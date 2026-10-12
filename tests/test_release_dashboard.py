# ABOUTME: Exercises release dashboard authorization through actual native session verification and HTTP requests.
# ABOUTME: Checks anonymous, unbound, revoked, and foreign-origin requests against a synthetic owner profile.
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import tempfile
from threading import Thread
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi import FastAPI
import uvicorn
from hermes_cli.dashboard_auth.middleware import gated_auth_middleware
from hermes_cli.dashboard_auth.registry import register_global_provider, unregister_global_provider
from plugins.dashboard_auth.basic import BasicAuthProvider, hash_password
from optional.lifeos_release_manager.dashboard.plugin_api import router
from lifeos_hook_bridge.memory_service import MemoryConfiguration


class ReleaseDashboardTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.profile = Path(self.folder.name) / '.hermes'
        self.profile.mkdir(mode=0o700)
        previous = os.environ.get('HERMES_HOME')
        os.environ['HERMES_HOME'] = str(self.profile)
        def restore_environment():
            if previous is None:
                os.environ.pop('HERMES_HOME', None)
            else:
                os.environ['HERMES_HOME'] = previous
        self.addCleanup(restore_environment)
        shutil.copytree(Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge',
            self.profile / 'plugins/lifeos-hook-bridge', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        self.configuration = MemoryConfiguration(self.profile / 'lifeos-memory.json')
        self.policy = {'version': 1, 'root': str(self.profile.parent / '.claude'), 'principal': 'synthetic-owner',
            'accounts': {'dashboard:basic:owner': 'synthetic-owner'}, 'destinations': {}, 'clients': {}}
        self.configuration.save(self.policy)
        secret = secrets.token_bytes(32)
        password_hash = hash_password('synthetic-password')
        provider = BasicAuthProvider(username='owner', password_hash=password_hash, secret=secret)
        register_global_provider(provider)
        self.addCleanup(unregister_global_provider, provider.name, provider)
        self.owner = provider.complete_password_login(username='owner', password='synthetic-password').access_token
        other = BasicAuthProvider(username='other', password_hash=password_hash, secret=secret)
        self.other = other.complete_password_login(username='other', password='synthetic-password').access_token
        app = FastAPI()
        app.state.auth_required = True
        app.middleware('http')(gated_auth_middleware)
        app.include_router(router, prefix='/api/plugins/lifeos-release-manager')
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        self.addCleanup(listener.close)
        self.origin = 'http://127.0.0.1:' + str(listener.getsockname()[1])
        self.server = uvicorn.Server(uvicorn.Config(app, log_level='critical', access_log=False, lifespan='off'))
        self.thread = Thread(target=self.server.run, kwargs={'sockets': [listener]})
        self.thread.start()
        def stop():
            self.server.should_exit = True
            self.thread.join(timeout=10)
            self.assertFalse(self.thread.is_alive())
        self.addCleanup(stop)
        deadline = time.monotonic() + 10
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() > deadline:
                self.fail('The actual dashboard authorization server does not start')
            time.sleep(0.01)

    def request(self, token=None, *, path='/operations', method='GET', body=None, origin=None):
        headers = {}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if origin:
            headers['Origin'] = origin
        request = Request(self.origin + '/api/plugins/lifeos-release-manager' + path,
            data=body, method=method, headers=headers)
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_native_sessions_enforce_owner_binding_and_current_revocation(self):
        self.assertEqual(self.request()[0], 401)
        self.assertEqual(self.request('forged-session')[0], 401)
        self.assertEqual(self.request(self.other)[0], 403)
        self.assertEqual(self.request(self.owner), (200, {'operations': []}))
        self.policy['accounts'] = {}
        self.configuration.save(self.policy)
        self.assertEqual(self.request(self.owner)[0], 403)

    def test_mutations_reject_foreign_origin_and_client_supplied_fields(self):
        path = '/operations/' + ('a' * 32) + '/review'
        self.assertEqual(self.request(self.owner, path=path, method='POST', origin='https://other.invalid')[0], 403)
        self.assertEqual(self.request(self.owner, path=path, method='POST', body=b'{"account":"owner"}', origin=self.origin)[0], 400)
        self.assertFalse((self.profile / '.lifeos-releases').exists())
