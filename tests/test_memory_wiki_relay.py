# ABOUTME: Tests native wiki HTTP requests through actual Hermes session authentication.
# ABOUTME: Checks current registered notes, retirement, failed connectors, and revoked access.
import json
from pathlib import Path
import subprocess
import os
import unittest

import httpx

from test_memory_native import OWNER
import test_memory_pulse_relay as relay_fixture


class MemoryWikiRelayTests(unittest.TestCase):
    native_module = 'wiki.ts'
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def note(self):
        native = self.fixture.fixture.fixture.fixture.fixture
        saved = native.remember('SyntheticWikiCurrentMarker', 'wiki-current')
        self.assertEqual(saved['status'], 'committed', saved)
        directory = self.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research'
        path = next(directory.glob('*.md'))
        unknown = directory / 'synthetic-wiki-unknown.md'
        unknown.write_text('---\nid: synthetic-wiki-unknown\ntitle: SyntheticWikiUnknownTitle\n'
                           'type: research\n---\nSyntheticWikiUnknownBody\n')
        return native.memory, saved['reference'], path

    def paths(self, slug):
        return ['/api/wiki', '/api/wiki/graph', '/api/wiki/search?q=SyntheticWiki',
                '/api/wiki/backlinks/' + slug, '/api/wiki/doc/' + slug,
                '/api/wiki/knowledge/research/' + slug]

    def test_ambient_owner_and_internal_flags_do_not_authorize_any_wiki_view(self):
        _, _, note = self.note()
        for path in self.paths(note.stem):
            with self.subTest(path=path):
                response = httpx.get(self.native + path, headers={'X-LifeOS-Owner': 'owner'})
                self.assertEqual(response.status_code, 401, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('SyntheticWiki', response.text)

    def test_authenticated_native_index_search_graph_and_body_use_registered_current_notes(self):
        _, _, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            results = []
            for path in self.paths(note.stem):
                response = client.get(self.native + path)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('etag', response.headers)
                results.append(response.json())
            self.assertIn('SyntheticWikiCurrentMarker', results[-1]['content'])
            self.assertEqual(results[-1]['category'], 'research')
            self.assertEqual(results[1]['nodes'][0]['id'], note.stem)
            self.assertIn('SyntheticWikiCurrentMarker', json.dumps(results[2]))
            self.assertNotIn('SyntheticWikiUnknown', json.dumps(results))
            self.assertEqual(client.get(self.native + '/api/wiki/doc/synthetic-wiki-unknown').status_code, 404)

    def test_correction_and_forget_replace_live_body_search_index_and_graph(self):
        memory, reference, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertIn('SyntheticWikiCurrentMarker', client.get(self.native + '/api/wiki/doc/' + note.stem).text)
            corrected = memory.correct(OWNER, reference, 'SyntheticWikiReplacementMarker', 'wiki-correct')
            self.assertEqual(corrected['status'], 'committed', corrected)
            self.assertIn('SyntheticWikiCurrentMarker', note.read_text())
            for path in self.paths(note.stem):
                response = client.get(self.native + path)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn('SyntheticWikiCurrentMarker', response.text)
            self.assertIn('SyntheticWikiReplacementMarker', client.get(self.native + '/api/wiki/doc/' + note.stem).text)
            forgotten = memory.forget(OWNER, corrected['reference'], 'wiki-forget')
            self.assertEqual(forgotten['status'], 'committed', forgotten)
            for path in self.paths(note.stem):
                response = client.get(self.native + path)
                self.assertEqual(response.status_code, 404 if '/doc/' in path or '/knowledge/' in path else 200,
                                 response.text)
                self.assertNotIn('SyntheticWikiReplacementMarker', response.text)
                self.assertNotIn('SyntheticWikiCurrentMarker', response.text)
            self.assertEqual(client.get(self.native + '/api/wiki/graph').json(), {'nodes': [], 'edges': []})

    def test_live_account_revocation_rechecks_every_wiki_view(self):
        _, _, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 200)
            self.fixture.configuration.update(lambda config: config['accounts'].pop('dashboard:basic:synthetic-owner'))
            for path in self.paths(note.stem):
                response = client.get(self.native + path)
                self.assertEqual(response.status_code, 403, response.text)
                self.assertNotIn('SyntheticWiki', response.text)

    def test_live_connector_loss_does_not_select_raw_wiki_or_existing_index(self):
        _, _, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 200)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            for path in self.paths(note.stem):
                response = client.get(self.native + path)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertNotIn('SyntheticWiki', response.text)

    def test_persistent_marker_refuses_raw_wiki_after_restart_without_connector(self):
        self.note()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        program = ('import {startWiki,stopWiki,handleWikiRequest} from '
            + json.dumps(str(self.root / 'LIFEOS/PULSE/modules/wiki.ts'))
            + ';startWiki();const response=await handleWikiRequest(new Request("http://localhost/api/wiki"),"/api/wiki");'
            + 'stopWiki();console.log(JSON.stringify({status:response?.status,body:await response?.text()}));')
        result = subprocess.run(['bun', '--no-install', '-e', program],
            env=dict(os.environ, HOME=str(self.fixture.home)), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        response = json.loads(result.stdout)
        self.assertEqual(response['status'], 503, response)
        self.assertNotIn('SyntheticWiki', response['body'])

    def test_managed_writes_reindex_and_scope_queries_do_not_admit_raw_paths(self):
        _, _, note = self.note()
        before = note.read_bytes()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            for method, path, status in [('PUT', '/api/wiki/doc/' + note.stem, 405),
                    ('POST', '/api/wiki/reindex', 405), ('GET', '/api/wiki/reindex', 404),
                    ('GET', '/api/wiki/skills', 404), ('GET', '/api/wiki?owner=other', 400),
                    ('GET', '/api/wiki/search?q=SyntheticWiki&root=other', 400),
                    ('GET', '/api/wiki/search?q=one&q=two', 400),
                    ('GET', '/api/wiki/search?q=one&limit=100000', 400)]:
                with self.subTest(method=method, path=path):
                    response = client.request(method, self.native + path, json={'content': 'Unreviewed edit'})
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertNotIn('SyntheticWiki', response.text)
        self.assertEqual(note.read_bytes(), before)

    def test_unavailable_dashboard_does_not_reuse_native_owner_data(self):
        _, _, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 200)
            self.server.should_exit = True
            self.thread.join(timeout=10)
            response = client.get(self.native + '/api/wiki/doc/' + note.stem)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticWiki', response.text)

    def test_cross_origin_requests_do_not_borrow_authenticated_owner_cookies(self):
        self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            response = client.get(self.native + '/api/wiki', headers={'Origin': 'https://untrusted.invalid'})
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('SyntheticWiki', response.text)
            self.assertEqual(client.get(self.native + '/api/wiki', headers={'Origin': self.native}).status_code, 200)

    def test_invalid_bearer_and_browser_logout_do_not_reuse_current_owner_view(self):
        self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 200)
            response = client.get(self.native + '/api/wiki', headers={'Authorization': 'Bearer invalid-synthetic'})
            self.assertEqual(response.status_code, 401, response.text)
            self.assertNotIn('SyntheticWiki', response.text)
            client.post(self.dashboard + '/auth/logout', follow_redirects=False)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 401)

    def test_changed_local_installation_cannot_supply_a_wiki_response(self):
        self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 200)
            self.fixture.configuration.update(lambda config: config.update(root=str(self.fixture.home / 'other-root')))
            response = client.get(self.native + '/api/wiki')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticWiki', response.text)

    def test_owner_and_anonymous_connections_do_not_share_the_wiki_index(self):
        from concurrent.futures import ThreadPoolExecutor
        self.note()
        with httpx.Client(timeout=20) as owner, httpx.Client(timeout=20) as anonymous:
            self.login(owner)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda client: client.get(self.native + '/api/wiki'), [owner, anonymous]))
            self.assertEqual([result.status_code for result in results], [200, 401])
            self.assertNotIn('SyntheticWiki', results[1].text)

    def test_changed_registered_source_is_unavailable_instead_of_serving_raw_content(self):
        _, _, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 200)
            note.write_text(note.read_text().replace('SyntheticWikiCurrentMarker', 'SyntheticWikiChangedMarker'))
            response = client.get(self.native + '/api/wiki/doc/' + note.stem)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticWiki', response.text)

    def test_invalid_connector_permissions_do_not_select_the_raw_native_reader(self):
        self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/wiki').status_code, 200)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').chmod(0o644)
            response = client.get(self.native + '/api/wiki')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticWiki', response.text)

    def test_wiki_category_follows_the_native_archive_directory(self):
        _, _, note = self.note()
        note.write_text(note.read_text().replace('type: research', 'type: idea    '))
        with httpx.Client(timeout=20) as client:
            self.login(client)
            response = client.get(self.native + '/api/wiki/knowledge/research/' + note.stem)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['category'], 'research')
            self.assertIn('type: idea', response.json()['content'])


if __name__ == '__main__':
    unittest.main()
