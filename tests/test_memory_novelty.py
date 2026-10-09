# ABOUTME: Checks novelty-state reads through real authenticated owner and native HTTP services.
# ABOUTME: Preserves native JSON output while excluding private, retired, and changed owner sources.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_operational_views as operational_fixture
from test_memory_native import OWNER


class MemoryNoveltyTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = operational_fixture.MemoryOperationalViewsTests.setUp
    create_fixture = operational_fixture.MemoryOperationalViewsTests.create_fixture
    native_module_name = operational_fixture.MemoryOperationalViewsTests.native_module_name
    stop_dashboard = operational_fixture.MemoryOperationalViewsTests.stop_dashboard
    stop_pulse = operational_fixture.MemoryOperationalViewsTests.stop_pulse
    login = operational_fixture.MemoryOperationalViewsTests.login
    original = operational_fixture.MemoryOperationalViewsTests.original

    def seed(self, marker='SyntheticNoveltyCurrent'):
        path = self.root / 'LIFEOS/MEMORY/STATE/novelty-state.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'runs': [{'id': 'synthetic-run', 'title': marker,
            'score': 0.7, 'details': {'reason': marker}}], 'lastUpdated': '2026-10-08T00:00:00Z'}))
        return path

    def test_anonymous_and_ambient_flags_cannot_authorize_novelty(self):
        self.seed()
        response = httpx.get(self.native + '/api/novelty', headers={'X-LifeOS-Owner': 'owner'})
        self.assertEqual(response.status_code, 401, response.text[:300])
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('SyntheticNoveltyCurrent', response.text[:300])

    def test_owner_preserves_native_json_shapes_and_source_bytes(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for value in ({'runs': [{'title': 'SyntheticNoveltyCurrent', 'score': 0.7}]},
                          ['SyntheticNoveltyCurrent'], 'SyntheticNoveltyCurrent', 17, True, None):
                with self.subTest(value=value):
                    path.write_text(json.dumps(value))
                    before = (path.read_bytes(), path.stat().st_mtime_ns)
                    response = client.get(self.native + '/api/novelty')
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json(), self.original('/api/novelty'))
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_missing_and_malformed_sources_preserve_native_empty_state(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for content in (None, '{unfinished', '', 'NaN'):
                with self.subTest(content=content):
                    if content is None: path.unlink(missing_ok=True)
                    else: path.write_text(content)
                    response = client.get(self.native + '/api/novelty')
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json(), self.original('/api/novelty'))
                    self.assertEqual(response.json(), {'runs': []})

    def test_private_and_escaped_nested_strings_do_not_enter_novelty(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for content in (json.dumps({'runs': [{'title': '<private>SyntheticNoveltyPrivate</private>'}]}),
                    '{"runs":[{"details":"{\\\"title\\\":\\\"\\\\u003cprivate\\\\u003eSyntheticNoveltyPrivate\\\\u003c/private\\\\u003e\\\"}"}]}'):
                with self.subTest(content=content):
                    path.write_text(content)
                    response = client.get(self.native + '/api/novelty')
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json(), {'runs': []})
                    self.assertNotIn('SyntheticNoveltyPrivate', response.text[:300])

    def test_forget_excludes_retained_novelty_without_changing_original(self):
        path = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticNoveltyCurrent',
            title='', project='', request_id='novelty-retained')
        memory.forget(OWNER, saved['reference'], 'novelty-forget')
        before = path.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/novelty')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), {'runs': []})
        self.assertEqual(path.read_bytes(), before)

    def test_revocation_and_missing_connector_cannot_select_raw_reader(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            response = client.get(self.native + '/api/novelty')
            self.assertEqual(response.status_code, 403, response.text[:300])
            self.assertNotIn('SyntheticNoveltyCurrent', response.text[:300])
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        response = httpx.get(self.native + '/api/novelty')
        self.assertEqual(response.status_code, 503, response.text[:300])
        self.assertNotIn('SyntheticNoveltyCurrent', response.text[:300])

    def test_methods_selectors_origin_and_invalid_bearer_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, target, headers, status in (
                    ('POST', '/api/novelty', {}, 405), ('GET', '/api/novelty?owner=other', {}, 400),
                    ('GET', '/api/novelty', {'Origin': 'https://outside.invalid'}, 403),
                    ('GET', '/api/novelty', {'Authorization': 'Bearer synthetic-invalid'}, 401)):
                with self.subTest(method=method, target=target):
                    response = client.request(method, self.native + target, headers=headers)
                    self.assertEqual(response.status_code, status, response.text[:300])
                    self.assertNotIn('SyntheticNoveltyCurrent', response.text[:300])

    def test_symlink_hardlink_and_oversize_sources_refuse(self):
        path = self.seed()
        before = path.read_bytes()
        outside = self.fixture.home / 'synthetic-novelty-outside.json'
        outside.write_bytes(before)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'oversize'):
                with self.subTest(mode=mode):
                    path.unlink()
                    if mode == 'symlink': path.symlink_to(outside)
                    elif mode == 'hardlink': os.link(outside, path)
                    else: path.write_text(json.dumps({'title': 'SyntheticNoveltyCurrent' + 'x' * (256 * 1024)}))
                    response = client.get(self.native + '/api/novelty')
                    self.assertEqual(response.status_code, 503, response.text[:300])
                    self.assertNotIn('SyntheticNoveltyCurrent', response.text[:300])
        self.assertEqual(outside.read_bytes(), before)

    def test_actual_render_rechecks_source_creation_inode_bytes_and_authority(self):
        for mode in ('source', 'created', 'metadata', 'authority'):
            with self.subTest(mode=mode):
                path = self.seed()
                if mode == 'created': path.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name(
                    'memory_novelty_process.py')), str(self.fixture.configuration.path), mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_exact_review_restores_safe_old_state_and_keeps_original_bytes(self):
        path = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticUnrelatedNoveltyRetirement',
            title='', project='', request_id='novelty-review-retained')
        memory.forget(OWNER, saved['reference'], 'novelty-review-forget')
        os.utime(path, (1_577_836_800, 1_577_836_800))
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        endpoint = self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/sources'
        paths = ['LIFEOS/MEMORY/STATE/novelty-state.json']
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/novelty')
            self.assertEqual(response.json(), {'runs': []})
            preview = client.post(endpoint + '/preview', json={'paths': paths})
            self.assertEqual(preview.status_code, 200, preview.text[:300])
            self.assertTrue(preview.json()['sources'][0]['accepted'])
            approval = client.post(endpoint, json={'paths': paths, 'signature': preview.json()['signature']})
            self.assertEqual(approval.status_code, 200, approval.text[:300])
            self.assertEqual(approval.json()['status'], 'committed')
            response = client.get(self.native + '/api/novelty')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), self.original('/api/novelty'))
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_invalid_utf8_refuses_without_source_disclosure(self):
        path = self.seed()
        path.write_bytes(b'{"note":"SyntheticNoveltyCurrent\xff"}')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/novelty')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticNoveltyCurrent', response.text)
