# ABOUTME: Checks actual Evals and ThreatModel HTTP routes against current owner source admission.
# ABOUTME: Compares native fields while refusing anonymous, private, retired, and redirected sources.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


class MemoryRegisteredModuleCases:
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def native_module_name(self): return 'memory.ts'

    def seed(self, marker='SyntheticRegisteredCurrent'):
        path = self.root / self.source_relative
        path.parent.mkdir(parents=True, exist_ok=True)
        body = json.loads(json.dumps(self.source_body).replace('MARKER', marker))
        path.write_text(json.dumps(body))
        return path

    def original(self):
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {handleRequest} from ' + json.dumps(str(control / 'LIFEOS/PULSE/modules' / self.native_module))
            + ';const response=await handleRequest(new Request("http://localhost"+' + json.dumps(self.route)
            + '),' + json.dumps(self.route) + ');console.log(await response.text());')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=30, env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root),
                LIFEOS_DIR=str(self.root / 'LIFEOS'), THREATMODEL_DATA_DIR=str(self.root / 'LIFEOS/USER/SECURITY/THREATMODEL')))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_anonymous_reader_cannot_read_native_labels_counts_or_presence(self):
        self.seed()
        response = httpx.get(self.native + self.route, headers={'X-LifeOS-Owner': 'owner'})
        self.assertEqual(response.status_code, 401, response.text[:300])
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('SyntheticRegisteredCurrent', response.text)

    def test_original_native_sources_absence_and_malformed_json_characterization(self):
        path = self.seed()
        body = self.original()
        if self.native_module == 'evals.ts':
            self.assertEqual(body['suites'][0], dict(self.source_body, suite='SyntheticRegisteredCurrent', type='regression'))
            path.unlink()
            self.assertEqual(self.original()['suites'], [])
            path.write_text('{"suite":')
            self.assertEqual(self.original()['suites'], [])
        else:
            self.assertEqual((body['grade'], body['total'], body['open'], body['overdue_review']), ('orange', 1, 1, 0))
            self.assertNotIn('notes', body['risks'][0])
            self.assertNotIn('history', body['risks'][0])
            path.unlink()
            self.assertFalse(self.original()['available'])
            path.write_text('{"risks":')
            malformed = self.original()
            self.assertFalse(malformed['available'])
            self.assertIn('SyntaxError', malformed['error'])

    def test_admitted_fields_and_absence_preserve_actual_native_response(self):
        path = self.seed()
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for missing in (False, True):
                if missing:
                    self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
                    path.unlink()
                response = client.get(self.native + self.route)
                self.assertEqual(response.status_code, 200, response.text[:300])
                body, original = response.json(), self.original()
                if 'register_age_ms' in body:
                    self.assertLess(abs(body.pop('register_age_ms') - original.pop('register_age_ms')), 1000)
                self.assertEqual(body, original)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_private_source_and_retirement_refuse_cached_native_result(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.seed()
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
            self.seed('<private>SyntheticRegisteredHidden</private>')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticRegisteredCurrent', response.text)
            self.assertNotIn('SyntheticRegisteredHidden', response.text)
            self.seed()
            memory = self.fixture.fixture.fixture.fixture.fixture.memory
            saved = memory.remember(OWNER, category='project', content='SyntheticRegisteredCurrent',
                title='Synthetic registered fixture', project='lab', request_id='registered-save')
            memory.forget(OWNER, saved['reference'], 'registered-forget')
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticRegisteredCurrent', response.text)

    def test_current_account_origin_and_connector_govern_delivery(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
            self.assertEqual(client.get(self.native + self.route, headers={'Origin': 'https://untrusted.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + self.route, headers={'Authorization': 'Bearer invalid'}).status_code, 401)
            self.fixture.configuration.update(lambda config: config['accounts'].clear())
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 403, response.text[:300])
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native + self.route).status_code, 503)

    def test_redirected_invalid_or_excessive_source_refuses(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
                with self.subTest(mode=mode):
                    path = self.root / self.source_relative
                    if path.exists() or path.is_symlink(): path.unlink()
                    path = self.seed()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'synthetic-registered-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'utf8': path.write_bytes(b'\xff')
                    else: path.write_bytes(b'x' * (256 * 1024 + 1))
                    response = client.get(self.native + self.route)
                    self.assertEqual(response.status_code, 503, response.text[:300])

    def test_methods_queries_and_unknown_routes_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, route, status in (('POST', self.route, 405), ('GET', self.route + '?owner=other', 400),
                    ('GET', self.route + '/unsupported', 404)):
                with self.subTest(route=route):
                    response = client.request(method, self.native + route)
                    self.assertEqual(response.status_code, status, response.text[:300])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_actual_native_render_rechecks_source_bytes_inode_creation_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                path = self.seed()
                if mode == 'created': path.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_registered_process.py')),
                    str(self.fixture.configuration.path), self.native_module[:-3], self.source_relative, mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_exact_review_restores_only_current_safe_old_source(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        path = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated registered retirement',
            title='', project='', request_id='registered-review-unrelated')
        memory.forget(OWNER, saved['reference'], 'registered-review-unrelated-forget')
        os.utime(path, (1, 1))
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + self.route).status_code, 503)
            selected = preview(memory, OWNER, [self.source_relative])
            self.assertTrue(selected['sources'][0]['accepted'], selected)
            self.assertEqual(approve(memory, OWNER, [self.source_relative], selected['signature'])['status'], 'committed')
            self.assertEqual(client.get(self.native + self.route).status_code, 200)
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)


class MemoryEvalsModuleTests(MemoryRegisteredModuleCases, unittest.TestCase):
    native_module = 'evals.ts'
    route = '/api/evals'
    source_relative = 'LIFEOS/MEMORY/STATE/Evals-Results/synthetic-suite/latest.json'
    source_body = {'suite': 'MARKER', 'passed': True, 'score': 0.75, 'pass_to_k': 0.5, 'pass_at_k': 1,
        'summary': 'Synthetic result', 'ts': '2026-10-08T00:00:00Z',
        'cases': [{'id': 'synthetic-case', 'mean_score': 0.75, 'pass_to_k': 0.5}]}

    def test_equal_timestamp_order_and_native_hidden_suite_selection(self):
        path = self.seed()
        directory = path.parent.parent
        for name in ('z-suite', 'a-suite', 'Ω-suite', '😀-suite'):
            target = directory / name / 'latest.json'
            target.parent.mkdir()
            target.write_text(json.dumps(dict(self.source_body, suite=name)))
        for name in ('.hidden', '__draft'):
            target = directory / name / 'latest.json'
            target.parent.mkdir()
            target.write_text('{"suite":"<private>SyntheticExcludedDraft</private>"}')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), self.original())
            self.assertNotIn('SyntheticExcludedDraft', response.text)

    def test_selected_suite_directory_name_is_rechecked_after_native_render(self):
        self.seed()
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_registered_process.py')),
            str(self.fixture.configuration.path), 'evals', self.source_relative, 'selection'],
            capture_output=True, text=True, timeout=30,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_suite_discovery_is_bounded(self):
        path = self.seed()
        for i in range(2048): (path.parent.parent / ('synthetic-entry-' + str(i))).mkdir()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + self.route)
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticRegisteredCurrent', response.text)


class MemoryThreatModelModuleTests(MemoryRegisteredModuleCases, unittest.TestCase):
    native_module = 'threatmodel.ts'
    route = '/api/threatmodel'
    source_relative = 'LIFEOS/USER/SECURITY/THREATMODEL/risk-register.json'
    source_body = {'updated': '2026-10-08T00:00:00Z', 'risks': [{'id': 'synthetic-risk', 'title': 'MARKER',
        'threat': 'Synthetic threat', 'level': 'High', 'score': 6, 'likelihood': 2, 'impact': 3,
        'status': 'open', 'assets': ['SyntheticAsset'], 'data_classes': ['synthetic'],
        'owner': 'Synthetic owner', 'response': 'mitigate', 'review_by': '2099-01-01',
        'notes': 'Synthetic omitted notes', 'history': ['Synthetic omitted history']}]}


if __name__ == '__main__': unittest.main()
