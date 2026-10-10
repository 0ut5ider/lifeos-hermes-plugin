# ABOUTME: Characterizes the native Menubar payload and its implicit Conduit initialization.
# ABOUTME: Requires current owner admission for personal counts and work labels on real HTTP routes.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import select
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from test_memory_native import OWNER

import httpx
import test_memory_pulse_relay as relay_fixture


class MemoryMenubarTests(unittest.TestCase):
    native_module = 'menubar.ts'
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def native_module_name(self): return 'memory.ts'

    def setUp(self):
        previous = {key: os.environ.get(key) for key in ('HERMES_HOME', 'AMBER_LEDGER_URL')}
        os.environ.pop('HERMES_HOME', None)
        os.environ['AMBER_LEDGER_URL'] = ''
        def restore():
            for key, value in previous.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value
        self.addCleanup(restore)
        relay_fixture.MemoryPulseRelayTests.setUp(self)
        pulse = self.root / 'LIFEOS/PULSE'
        public = pulse.resolve()
        pulse.unlink()
        pulse.mkdir()
        for entry in public.iterdir():
            if entry.name != 'state': (pulse / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())

    def seed(self, marker='SyntheticMenubarCurrent'):
        now = datetime.now(timezone.utc).isoformat()
        work = self.root / 'LIFEOS/MEMORY/STATE/work.json'
        work.write_text(json.dumps({'sessions': {'synthetic': {'task': marker, 'phase': 'design', 'updatedAt': now}}}))
        log = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl'
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(json.dumps({'ts': now, 'target_kind': marker}) + '\n')
        return work, log

    def original(self):
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {handleRequest} from ' + json.dumps(str(control / 'LIFEOS/PULSE/modules/menubar.ts'))
            + ';const response=await handleRequest(new Request("http://localhost/api/menubar"),"/api/menubar");console.log(await response.text());')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    @staticmethod
    def stable(body):
        if isinstance(body, dict): return {k: MemoryMenubarTests.stable(v) for k, v in body.items()
            if k not in ('generatedAt', 'ago', 'uptimeSec')}
        if isinstance(body, list): return [MemoryMenubarTests.stable(v) for v in body]
        return body

    def test_original_native_payload_counts_feed_and_initialization_characterization(self):
        self.seed()
        body = self.original()
        self.assertEqual(body['counts']['work'], 1)
        self.assertEqual(body['counts']['memory'], 1)
        self.assertEqual(body['counts']['amber'], 0)
        self.assertEqual(body['hermes'], {'status': 'down', 'summary': 'gateway down', 'channels': ''})
        self.assertIn('SyntheticMenubarCurrent', json.dumps(body['feed']))
        self.assertTrue((self.root / 'LIFEOS/USER/CONDUIT/config.json').is_file())

    def test_anonymous_reader_refuses_labels_counts_and_implicit_write(self):
        self.seed()
        response = httpx.get(self.native + '/api/menubar')
        self.assertEqual(response.status_code, 401, response.text[:300])
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('SyntheticMenubarCurrent', response.text)
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/config.json').exists())

    def test_owner_admitted_fields_match_actual_native_payload(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for suffix in ('', '/'):
                response = client.get(self.native + '/api/menubar' + suffix)
                self.assertEqual(response.status_code, 200, response.text[:300])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertEqual(self.stable(response.json()), self.stable(self.original()))

    def test_private_work_source_refuses_cached_personal_labels(self):
        self.seed('<private>SyntheticMenubarHidden</private>')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/menubar')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticMenubarHidden', response.text)

    def test_current_owner_origin_bearer_and_connector_govern_delivery(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/menubar').status_code, 200)
            self.assertEqual(client.get(self.native + '/api/menubar', headers={'Origin': 'https://untrusted.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + '/api/menubar', headers={'Authorization': 'Bearer invalid'}).status_code, 401)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(client.get(self.native + '/api/menubar').status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native + '/api/menubar').status_code, 503)

    def test_unknown_methods_and_public_selectors_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, target, code in (('POST', '/api/menubar', 405), ('GET', '/api/menubar?profile=other', 400),
                    ('GET', '/api/menubar/unsupported', 404)):
                response = client.request(method, self.native + target)
                self.assertEqual(response.status_code, code, response.text[:300])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/config.json').exists())

    def test_redirected_invalid_or_excessive_work_source_refuses(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
                with self.subTest(mode=mode):
                    path = self.root / 'LIFEOS/MEMORY/STATE/work.json'
                    path.unlink(missing_ok=True)
                    path, _ = self.seed()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'menubar-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'utf8': path.write_bytes(b'\xff')
                    else: path.write_bytes(b'x' * (256 * 1024 + 1))
                    self.assertEqual(client.get(self.native + '/api/menubar').status_code, 503)

    def test_admitted_daemon_job_counts_preserve_native_metadata(self):
        self.seed()
        directory = self.root / 'LIFEOS/PULSE/state'
        directory.mkdir()
        state = directory / 'state.json'
        state.write_text(json.dumps({'startedAt': int(datetime.now().timestamp() * 1000) - 3000,
            'jobs': {'synthetic': {'consecutiveFailures': 3, 'lastRun': int(datetime.now().timestamp() * 1000)}}}))
        (directory / 'pulse.pid').write_text(str(os.getpid()))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/menubar')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json()['daemon']['failingJobs'], 1)
            self.assertEqual(self.stable(response.json()), self.stable(self.original()))
            state.write_text(json.dumps({'jobs': {'synthetic': {'note': '<private>SyntheticMenubarHidden</private>'}}}))
            response = client.get(self.native + '/api/menubar')
            self.assertEqual(response.status_code, 503, response.text[:300])

    def test_private_gateway_metadata_refuses_without_reading_credentials(self):
        self.seed()
        profile = self.fixture.profile
        (profile / 'gateway_state.json').write_text(json.dumps({'updated_at': datetime.now(timezone.utc).isoformat(),
            'platforms': {'discord': {'state': 'fatal', 'error_message': '<private>SyntheticMenubarHidden</private>'}}}))
        env = profile / '.env'
        env.write_text('SYNTHETIC_CREDENTIAL_FIXTURE=do-not-read\n')
        before = (env.read_bytes(), env.stat().st_mtime_ns, env.stat().st_atime_ns)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/menubar')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticMenubarHidden', response.text)
        self.assertEqual((env.stat().st_mtime_ns, env.stat().st_atime_ns), before[1:])
        self.assertEqual(env.read_bytes(), before[0])

    def test_private_or_retired_telemetry_does_not_contribute_counts(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for retired in (False, True):
                timestamp = datetime.now(timezone.utc).isoformat()
                if retired:
                    memory = self.fixture.fixture.fixture.fixture.fixture.memory
                    saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticMenubarAuditRetired',
                        title='', project='', request_id='menubar-retired-save')
                    memory.forget(OWNER, saved['reference'], 'menubar-retired-forget')
                _, log = self.seed()
                marker = 'SyntheticMenubarAuditRetired' if retired else '<private>SyntheticMenubarHidden</private>'
                log.write_text(json.dumps({'ts': timestamp, 'target_kind': marker}) + '\n')
                config = self.root / 'LIFEOS/USER/CONDUIT/config.json'
                config.parent.mkdir(parents=True, exist_ok=True)
                config.write_text('{"pollIntervalSec":120}')
                response = client.get(self.native + '/api/menubar')
                self.assertEqual(response.status_code, 200, response.text[:300])
                self.assertEqual(response.json()['counts']['memory'], 0)
                self.assertNotIn('SyntheticMenubarHidden', response.text)
                self.assertNotIn('SyntheticMenubarAuditRetired', response.text)

    def test_managed_direct_conduit_accessor_requires_admitted_inputs(self):
        script = ('import {todayRecordPublic} from ' + json.dumps(str(self.root / 'LIFEOS/PULSE/modules/conduit.ts'))
            + ';try {todayRecordPublic();console.log(JSON.stringify({refused:false}));}'
            + 'catch {console.log(JSON.stringify({refused:true}));}')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'refused': True})
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/config.json').exists())

    def test_actual_render_rechecks_source_inode_creation_profile_descriptor_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority', 'descriptor', 'profile'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                path, _ = self.seed()
                if mode == 'created': path.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_menubar_process.py')),
                    str(self.fixture.configuration.path), path.relative_to(self.root).as_posix(), mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_exact_review_preserves_configured_profile_and_work_source_bytes(self):
        from lifeos_hook_bridge.memory_access import NativeMemory
        from lifeos_hook_bridge.memory_source_review import preview, approve
        work, _ = self.seed()
        profile = self.fixture.profile
        gateway = profile / 'gateway_state.json'
        gateway.write_text(json.dumps({'updated_at': datetime.now(timezone.utc).isoformat(),
            'platforms': {'discord': {'state': 'connected'}}}))
        config = self.root / 'LIFEOS/USER/CONDUIT/config.json'
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('{"pollIntervalSec":120}')
        memory = NativeMemory(self.root, profile=profile)
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated Menubar retirement',
            title='', project='', request_id='menubar-review-save')
        memory.forget(OWNER, saved['reference'], 'menubar-review-forget')
        paths = [work, gateway, config]
        for path in paths: os.utime(path, (1, 1))
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
        names = ['LIFEOS/MEMORY/STATE/work.json', 'HERMES/gateway_state.json', 'LIFEOS/USER/CONDUIT/config.json']
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/menubar').status_code, 503)
            selected = preview(memory, OWNER, names)
            self.assertTrue(all(row['accepted'] for row in selected['sources']), selected)
            self.assertEqual(approve(memory, OWNER, names, selected['signature'])['status'], 'committed')
            response = client.get(self.native + '/api/menubar')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json()['hermes']['channels'], '1/1')
            self.assertEqual(response.json()['counts']['work'], 1)
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in paths], before)

    def test_configured_optional_remote_refuses_before_token_read_or_network_request(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                body = b'{"captures":[{"title":"SyntheticMenubarAmber"}]}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def stop():
            server.shutdown()
            server.server_close()
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        token = self.fixture.home / '.config/arbol/config.yaml'
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text('auth_token: synthetic-loopback-token\n')
        os.utime(token, (1, 1))
        self.stop_pulse()
        self.process = subprocess.Popen(['bun', '--no-install', str(self.fixture.home / 'pulse-relay.ts')],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=dict(os.environ, HOME=str(self.fixture.home), AMBER_LEDGER_URL=f'http://127.0.0.1:{server.server_port}'))
        self.assertTrue(select.select([self.process.stdout], [], [], 10)[0])
        self.native = f'http://127.0.0.1:{int(self.process.stdout.readline())}'
        self.assertEqual(httpx.get(self.native + '/api/menubar').status_code, 401)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/menubar')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertEqual(requests, [])
        self.assertEqual(token.stat().st_atime_ns, 1000000000)
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/config.json').exists())


if __name__ == '__main__': unittest.main()
