# ABOUTME: Checks native user index responses through actual authenticated owner HTTP sessions.
# ABOUTME: Compares native calculations and refuses stale, private, redirected, or revoked source access.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_life_relay as life_fixture


class MemoryUserIndexTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = life_fixture.MemoryLifeRelayTests.setUp
    create_fixture = life_fixture.MemoryLifeRelayTests.create_fixture
    native_module_name = life_fixture.MemoryLifeRelayTests.native_module_name
    stop_dashboard = life_fixture.MemoryLifeRelayTests.stop_dashboard
    stop_pulse = life_fixture.MemoryLifeRelayTests.stop_pulse
    login = life_fixture.MemoryLifeRelayTests.login

    def seed(self):
        path = self.root / 'LIFEOS/USER/TELOS/GOALS.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\ncategory: domain\nkind: collection\npublish: daemon-summary\nreview_cadence: 30\n---\n'
            '# SyntheticIndexedGoals\n- **SyntheticIndexedGoal**\n')
        self.cache = self.root / 'LIFEOS/PULSE/state/user-index.json'
        self.control()
        return path

    def control(self):
        source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        result = subprocess.run(['bun', '--no-install', str(source / 'LIFEOS/PULSE/modules/user-index.ts'), '--json'],
            env=dict(os.environ, HOME=str(self.fixture.home), LIFEOS_DIR=str(self.root / 'LIFEOS')),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def get(self, client, query=''):
        return client.get(self.native + '/api/user-index' + query)

    def test_anonymous_and_ambient_owner_cannot_read_index(self):
        self.seed()
        response = httpx.get(self.native + '/api/user-index', headers={'X-LifeOS-Owner': 'owner'})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertNotIn('SyntheticIndexedGoal', response.text)

    def test_all_native_index_slices_preserve_current_fields(self):
        self.seed()
        expected = self.control()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            for filter_name, key in (('', None), ('stats', 'stats'), ('publish', 'publish_feed'),
                                     ('stale', 'stale_queue'), ('gaps', 'interview_gaps')):
                with self.subTest(filter=filter_name):
                    response = self.get(client, '?filter=' + filter_name if filter_name else '')
                    self.assertEqual(response.status_code, 200, response.text[:500])
                    body = response.json()
                    if key is None:
                        self.assertIsInstance(body['generated_at'], str)
                        body['generated_at'] = expected['generated_at']
                    self.assertEqual(body, expected[key] if key else expected)
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_cache_cannot_restore_old_or_private_source_preview(self):
        path = self.seed()
        path.write_text('# SyntheticIndexedChangedGoal\nSynthetic current content\n')
        with httpx.Client(timeout=35) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('SyntheticIndexedChangedGoal', response.text)
            self.assertNotIn('SyntheticIndexedGoals', response.text)
            path.write_text('# SyntheticIndexedPrivateGoal\n<private>SyntheticIndexedPrivateContent</private>\n')
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticIndexedPrivate', response.text)
        self.assertIn('SyntheticIndexedGoals', self.cache.read_text())

    def test_revoked_owner_and_missing_connector_cannot_read_index(self):
        self.seed()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
            data = connector.read_bytes()
            connector.unlink()
            self.assertEqual(self.get(client).status_code, 503)
            connector.write_bytes(data)
            connector.chmod(0o600)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(self.get(client).status_code, 403)

    def test_redirected_or_hardlinked_source_cannot_publish(self):
        path = self.seed()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            external = self.fixture.home / 'synthetic-index-source.md'
            path.rename(external)
            path.symlink_to(external)
            self.assertEqual(self.get(client).status_code, 503)
            path.unlink()
            path.write_bytes(external.read_bytes())
            os.link(path, self.fixture.home / 'synthetic-index-source-alias.md')
            self.assertEqual(self.get(client).status_code, 503)

    def test_forgotten_source_cannot_return_from_cache_and_safe_review_restores_current_source(self):
        path = self.seed()
        before = path.read_bytes(), path.stat().st_mtime_ns
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: SyntheticUnrelatedIndexRetirement',
            title='', project='', request_id='synthetic-index-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-index-forget')
        relative = 'LIFEOS/USER/TELOS/GOALS.md'
        endpoint = '/api/plugins/lifeos-hook-bridge/memory/sources'
        with httpx.Client(timeout=35) as client:
            self.login(client)
            self.assertNotIn('SyntheticIndexedGoal', self.get(client).text)
            preview = client.post(self.dashboard + endpoint + '/preview', json={'paths': [relative]})
            self.assertEqual(preview.status_code, 200, preview.text)
            snapshot = preview.json()
            approved = client.post(self.dashboard + endpoint, json={'paths': [relative], 'signature': snapshot['signature']})
            self.assertEqual(approved.json()['status'], 'committed', approved.text)
            self.assertIn('SyntheticIndexedGoal', self.get(client).text)
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.assertIn('SyntheticIndexedGoal', self.cache.read_text())

    def test_retired_source_filename_cannot_return_from_current_source(self):
        self.seed()
        label = 'SyntheticRetiredIndexLabel'
        path = self.root / ('LIFEOS/USER/TELOS/' + label + '.md')
        path.write_text('# Synthetic safe retained index title\n')
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: ' + label,
            title='', project='', request_id='synthetic-index-label-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-index-label-forget')
        import time
        os.utime(path, ns=(time.time_ns(), time.time_ns()))
        with httpx.Client(timeout=35) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn(label, response.text)
            self.assertNotIn('Synthetic safe retained index title', response.text)

    def test_native_skip_directories_and_depth_remain_intact(self):
        self.seed()
        for relative in ('Security/SyntheticSkip.md', 'Credentials/SyntheticSkip.md',
                         'synthetic-domain/level-one/level-two/SyntheticSkip.md'):
            path = self.root / 'LIFEOS/USER' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# SyntheticSkippedIndexSource\n')
        expected = self.control()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            body = self.get(client).json()
            body['generated_at'] = expected['generated_at']
            self.assertEqual(body, expected)
            self.assertNotIn('SyntheticSkippedIndexSource', json.dumps(body))

    def test_method_origin_bearer_and_selectors_cannot_borrow_owner_session(self):
        self.seed()
        with httpx.Client(timeout=35) as client:
            self.login(client)
            for method, query, headers, expected in (
                ('POST', '', {}, 405), ('GET', '', {'Origin': 'https://synthetic.invalid'}, 403),
                ('GET', '', {'Authorization': 'Bearer synthetic-invalid'}, 401),
                ('GET', '?owner=other', {}, 400), ('GET', '?filter=unknown', {}, 400),
                ('GET', '?filter=stats&filter=publish', {}, 400)):
                with self.subTest(method=method, query=query):
                    response = client.request(method, self.native + '/api/user-index' + query, headers=headers)
                    self.assertEqual(response.status_code, expected, response.text)
                    self.assertNotIn('SyntheticIndexedGoal', response.text)

    def test_source_and_discovery_budgets_refuse_before_returning_content(self):
        path = self.seed()
        path.write_text('SyntheticOversizeIndex' * 16000)
        with httpx.Client(timeout=35) as client:
            self.login(client)
            self.assertEqual(self.get(client).status_code, 503)
            path.write_text('# Synthetic bounded source\n')
            directory = self.root / 'LIFEOS/USER/synthetic-discovery'
            directory.mkdir()
            for number in range(2049): (directory / str(number)).touch()
            self.assertEqual(self.get(client).status_code, 503)

    def test_source_creation_and_authority_change_after_native_render_withhold_output(self):
        self.seed()
        for mode in ('source', 'created', 'authority'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_life_process.py')),
                    str(self.fixture.configuration.path), mode, '/api/user-index'], capture_output=True, text=True,
                    timeout=40, env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})


if __name__ == '__main__':
    unittest.main()
