# ABOUTME: Checks native Books, Projects, and Assets routes through authenticated owner HTTP.
# ABOUTME: Preserves native parsing while excluding private, retired, and redirected owner sources.
import json
import os
from pathlib import Path
import subprocess
import sys
import select
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


class MemoryPersonalModuleCases:
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def native_module_name(self): return 'memory.ts'

    def seed(self, marker='SyntheticPersonalModuleCurrent'):
        path = self.root / self.source_relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.source_text.replace('MARKER', marker))
        for relative, text in getattr(self, 'additional_sources', {}).items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        return path

    def original(self, route, *, running=False, drift=False):
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {handleRequest,start} from ' + json.dumps(str(control / 'LIFEOS/PULSE/modules' / self.native_module))
            + ';\n' + ('start();\n' if running else '') + 'const result=await handleRequest(new Request("http://localhost"+' + json.dumps(route) + '),'
            + json.dumps(route) + ');console.log(await result.text());')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=30, env=dict(os.environ, HOME=str(self.fixture.home)))
        self.assertEqual(result.returncode, 0, result.stderr)
        if drift:
            self.assertIn('source format drifted', result.stderr)
            self.assertEqual(len(result.stderr.splitlines()), 1)
        else: self.assertEqual(result.stderr, '')
        body = json.loads(result.stdout.splitlines()[-1])
        body.pop('generatedAt', None)
        return body

    def start_module(self):
        self.stop_pulse()
        program = self.fixture.home / 'pulse-relay.ts'
        text = program.read_text().replace('{handleRequest}', '{handleRequest,start}').replace('const server=', 'start();\nconst server=')
        program.write_text(text)
        self.process = subprocess.Popen(['bun', '--no-install', str(program)], env=dict(os.environ,
            HOME=str(self.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1'), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.assertTrue(select.select([self.process.stdout], [], [], 10)[0])
        self.assertEqual(self.process.stdout.readline().strip(), '[' + self.native_module[:-3] + '] started')
        self.native = f'http://127.0.0.1:{int(self.process.stdout.readline())}'

    def test_started_native_runtime_and_absent_sources_match_original(self):
        self.seed()
        self.start_module()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for missing in (False, True):
                if missing: (self.root / self.source_relative).unlink()
                for suffix in ('', '/status', '/health'):
                    with self.subTest(missing=missing, suffix=suffix):
                        response = client.get(self.native + self.route + suffix)
                        self.assertEqual(response.status_code, 200, response.text[:300])
                        body = response.json()
                        body.pop('generatedAt', None)
                        self.assertEqual(body, self.original(self.route + suffix, running=True))

    def test_exact_review_restores_safe_old_sources_without_rewriting(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        path = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated module retirement',
            title='', project='', request_id='personal-review-unrelated')
        memory.forget(OWNER, saved['reference'], 'personal-review-unrelated-forget')
        relatives = [self.source_relative, *getattr(self, 'additional_sources', {})]
        for relative in relatives: os.utime(self.root / relative, (1, 1))
        before = [(self.root / relative).read_bytes() for relative in relatives]
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 503)
            selected = preview(memory, OWNER, relatives)
            self.assertTrue(all(row['accepted'] for row in selected['sources']), selected)
            self.assertEqual(approve(memory, OWNER, relatives, selected['signature'])['status'], 'committed')
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
        self.assertEqual([(self.root / relative).read_bytes() for relative in relatives], before)
        self.assertEqual(path.stat().st_mtime_ns, 1000000000)

    def test_native_render_rechecks_bytes_inode_missing_source_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                path = self.seed()
                if mode == 'created': path.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_personal_process.py')),
                    str(self.fixture.configuration.path), self.native_module[:-3], self.source_relative, mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_anonymous_and_ambient_flags_cannot_read_module_data_or_counts(self):
        self.seed()
        for suffix in ('', '/list', '/status', '/health'):
            with self.subTest(suffix=suffix):
                response = httpx.get(self.native + self.route + suffix, headers={'X-LifeOS-Owner': 'owner'})
                self.assertEqual(response.status_code, 401, response.text[:300])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('SyntheticPersonalModuleCurrent', response.text)

    def test_admitted_module_fields_match_original_native_parsing(self):
        path = self.seed()
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for suffix in ('', '/list', '/status', '/health'):
                with self.subTest(suffix=suffix):
                    response = client.get(self.native + self.route + suffix)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    body = response.json()
                    body.pop('generatedAt', None)
                    self.assertEqual(body, self.original(self.route + suffix))
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertIn('SyntheticPersonalModuleCurrent', client.get(self.native + self.route).text)
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_private_and_retired_source_cannot_reappear(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.seed('<private>SyntheticPersonalModuleHidden</private>')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticPersonalModuleHidden', response.text)
            self.seed()
            memory = self.fixture.fixture.fixture.fixture.fixture.memory
            saved = memory.remember(OWNER, category='project', content='SyntheticPersonalModuleCurrent',
                title='Synthetic module fixture', project='lab', request_id='personal-module-save')
            memory.forget(OWNER, saved['reference'], 'personal-module-forget')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticPersonalModuleCurrent', response.text)

    def test_current_account_connector_and_origin_govern_each_delivery(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
            response = client.get(self.native + self.route, headers={'Origin': 'https://untrusted.invalid'})
            self.assertEqual(response.status_code, 403, response.text[:300])
            response = client.get(self.native + self.route, headers={'Authorization': 'Bearer invalid'})
            self.assertEqual(response.status_code, 401, response.text[:300])
            self.fixture.configuration.update(lambda config: config['accounts'].clear())
            self.assertEqual(client.get(self.native + self.route).status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticPersonalModuleCurrent', response.text)

    def test_links_invalid_bytes_and_source_limits_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
                with self.subTest(mode=mode):
                    path = self.root / self.source_relative
                    if path.exists() or path.is_symlink(): path.unlink()
                    path = self.seed()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'synthetic-module-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'utf8': path.write_bytes(b'\xff')
                    else: path.write_bytes(b'x' * (256 * 1024 + 1))
                    response = client.get(self.native + self.route)
                    self.assertEqual(response.status_code, 503, response.text[:300])

    def test_methods_unknown_routes_and_selectors_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, route, status in (('POST', self.route, 405), ('GET', self.route + '?owner=other', 400),
                    ('GET', self.route + '/unsupported', 404)):
                with self.subTest(route=route):
                    response = client.request(method, self.native + route)
                    self.assertEqual(response.status_code, status, response.text[:300])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')


class MemoryBooksModuleTests(MemoryPersonalModuleCases, unittest.TestCase):
    native_module = 'books.ts'
    route = '/api/books'
    source_relative = 'LIFEOS/USER/BOOKS.md'
    source_text = '# Books\n## Synthetic category\n- title: "MARKER"\n  author: "Synthetic Author"\n  year: 2026\n  rating: 5\n  themes: [synthetic, local]\n  canonical: true\n'


class MemoryProjectsModuleTests(MemoryPersonalModuleCases, unittest.TestCase):
    native_module = 'projects.ts'
    route = '/api/projects'
    source_relative = 'LIFEOS/USER/PROJECTS.md'
    source_text = '| Project | Path | URL | Deploy | Stack |\n| --- | --- | --- | --- | --- |\n| **MARKER** | `/synthetic` | https://example.invalid | local | Python |\n'
    additional_sources = {'LIFEOS/USER/TELOS/TELOS.md': '', 'LIFEOS/USER/PROJECTS_RETIRED.md': ''}

    def test_native_project_drift_is_preserved(self):
        self.seed()
        (self.root / self.source_relative).write_text('# Synthetic changed project format\n')
        self.start_module()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for suffix in ('', '/health'):
                response = client.get(self.native + self.route + suffix)
                self.assertEqual(response.status_code, 200, response.text[:300])
                body = response.json()
                body.pop('generatedAt', None)
                self.assertEqual(body, self.original(self.route + suffix, running=True, drift=True))
            self.assertEqual(client.get(self.native + self.route + '/health').json()['status'], 'degraded')


class MemoryAssetsModuleTests(MemoryPersonalModuleCases, unittest.TestCase):
    native_module = 'assets.ts'
    route = '/api/assets'
    source_relative = 'LIFEOS/USER/GEAR.md'
    source_text = '---\nlast_updated: 2026-10-08\n---\n## Devices\n| Item | Model | Use |\n| --- | --- | --- |\n| **Laptop** | MARKER | Work |\n'

    def network(self):
        self.seed()
        directory = self.root / 'LIFEOS/MEMORY/_NETWORK'
        directory.mkdir(parents=True, exist_ok=True)
        text = '## Network\n| Device | IP |\n| --- | --- |\n| MARKER | 10.20.30.40 |\n'
        (directory / 'topology-snapshot-001.md').write_text(text.replace('MARKER', 'SyntheticOlderTopology'))
        newest = directory / 'topology-snapshot-002.md'
        newest.write_text(text.replace('MARKER', 'SyntheticNewestTopology'))
        assets = directory / 'assets.json'
        assets.write_text(json.dumps({'assets': {'one': {'name': 'SyntheticEndpoint'}, 'two': {}}}))
        return directory, newest, assets

    def test_native_newest_snapshot_and_endpoint_counts_match(self):
        self.network()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text[:300])
            body = response.json()
            body.pop('generatedAt', None)
            self.assertEqual(body, self.original(self.route))
            self.assertIn('SyntheticNewestTopology', response.text)
            self.assertNotIn('SyntheticOlderTopology', response.text)

    def test_excluded_selected_topology_or_endpoint_source_has_no_fallback(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for selected in ('topology', 'endpoints'):
                directory, newest, assets = self.network()
                path = newest if selected == 'topology' else assets
                path.write_text(path.read_text().replace('Synthetic', '<private>SyntheticHidden</private>'))
                response = client.get(self.native + self.route)
                self.assertEqual(response.status_code, 503, response.text[:300])
                self.assertNotIn('SyntheticOlderTopology', response.text)
                self.assertNotIn('SyntheticHidden', response.text)

    def test_native_render_rechecks_snapshot_filename_selection(self):
        directory, newest, _ = self.network()
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_personal_process.py')),
            str(self.fixture.configuration.path), 'assets', str(newest.relative_to(self.root)), 'selection'],
            capture_output=True, text=True, timeout=30,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_topology_directory_discovery_is_bounded(self):
        directory, _, _ = self.network()
        for i in range(2046): (directory / ('synthetic-entry-' + str(i))).touch()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticNewestTopology', response.text)


if __name__ == '__main__': unittest.main()
