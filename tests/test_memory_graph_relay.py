# ABOUTME: Exercises the native graph HTTP view through actual Hermes session authentication.
# ABOUTME: Checks current graph data, stale cache refusal, retirement, revocation, and standalone output.
import json
import unittest

import httpx

from test_memory_native import OWNER
import test_memory_pulse_relay as relay_fixture
import test_memory_wiki_relay as wiki_fixture


class MemoryGraphRelayTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login
    note = wiki_fixture.MemoryWikiRelayTests.note

    def poison(self):
        graph = self.root / 'LIFEOS/MEMORY/GRAPH/graph.json'
        graph.parent.mkdir(exist_ok=True)
        graph.write_text(json.dumps({'generated': '2026-10-01T00:00:00Z', 'nodeCount': 1, 'edgeCount': 0,
            'nodes': [{'id': 'synthetic-raw-cache', 'title': 'SyntheticUnadmittedGraphCache', 'type': 'research',
                'degree': 0, 'tags': [], 'pagerank': 1, 'silo': 'knowledge', 'community': 0}], 'edges': []}))
        return graph

    def test_anonymous_graph_read_cannot_borrow_ambient_owner_authority(self):
        self.note(); self.poison()
        response = httpx.get(self.native + '/api/memory/graph', headers={'X-LifeOS-Owner': 'owner'})
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('Synthetic', response.text)

    def test_owner_graph_renders_registered_notes_and_keeps_cache_unchanged(self):
        self.note()
        graph = self.poison(); before = graph.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/memory/graph')
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body['nodeCount'], 1)
            self.assertEqual(body['edgeCount'], 0)
            self.assertEqual(body['nodes'][0]['title'], 'Synthetic lab routing')
            self.assertEqual(body['nodes'][0]['category'], 'research')
            self.assertEqual(body['nodes'][0]['backlinkCount'], 0)
            self.assertAlmostEqual(body['nodes'][0]['pagerank'], 1)
            self.assertEqual(body['nodes'][0]['silo'], 'knowledge')
            self.assertEqual(body['themes'], [])
            self.assertIsInstance(body['built'], str)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertNotIn('SyntheticUnadmittedGraphCache', response.text)
            self.assertNotIn('SyntheticWikiUnknown', response.text)
        self.assertEqual(graph.read_bytes(), before)

    def test_forgetting_removes_the_note_from_existing_authenticated_graph_requests(self):
        memory, reference, note = self.note()
        before = note.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/memory/graph')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['nodeCount'], 1)
            self.assertEqual(memory.forget(OWNER, reference, 'graph-http-forget')['status'], 'committed')
            response = client.get(self.native + '/api/memory/graph')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['nodeCount'], 0)
            self.assertEqual(response.json()['nodes'], [])
            self.assertNotIn('Synthetic lab routing', response.text)
        self.assertEqual(note.read_bytes(), before)

    def test_revocation_and_connector_loss_refuse_without_raw_cache_fallback(self):
        self.note(); self.poison()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/memory/graph').status_code, 200)
            self.fixture.configuration.update(lambda config: config['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = client.get(self.native + '/api/memory/graph')
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('Synthetic', response.text)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.get(self.native + '/api/memory/graph')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticUnadmittedGraphCache', response.text)

    def test_query_writes_and_cross_origin_requests_refuse_before_source_delivery(self):
        self.note()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, suffix, status, headers in [('POST', '', 405, {}),
                    ('GET', '?root=foreign', 400, {}), ('GET', '', 403, {'Origin': 'http://foreign.invalid'})]:
                with self.subTest(method=method, suffix=suffix, headers=headers):
                    response = client.request(method, self.native + '/api/memory/graph' + suffix, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertNotIn('Synthetic lab routing', response.text)
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_standalone_graph_keeps_native_cache_response_shape(self):
        self.poison()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.marker.unlink()
        response = httpx.get(self.native + '/api/memory/graph')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['nodes'][0]['title'], 'SyntheticUnadmittedGraphCache')
        self.assertEqual(body['nodeCount'], 1)
        self.assertEqual(body['edges'], [])
        self.assertEqual(body['themes'], [])
        self.assertEqual(body['built'], '2026-10-01T00:00:00Z')

    def test_graph_http_preserves_cross_silo_nodes_and_links(self):
        self.note()
        root = self.root / 'LIFEOS/MEMORY'
        for relative, title in [('WORK/synthetic-work/ISA.md', 'Synthetic graph work'),
                ('WISDOM/FRAMES/nested/frame.md', 'Synthetic graph wisdom'),
                ('LEARNING/SYNTHESIS/lesson.md', 'Synthetic graph synthesis')]:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('---\ntitle: "' + title + '"\ntags: [synthetic]\n---\n[[synthetic-lab-routing]]\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/memory/graph')
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body['nodeCount'], 4)
            self.assertEqual({node['silo'] for node in body['nodes']},
                             {'knowledge', 'work', 'wisdom', 'synthesis'})
            self.assertTrue(body['edges'], body)
            self.assertTrue(all('source' in edge and 'target' in edge for edge in body['edges']))
            self.assertAlmostEqual(sum(node['pagerank'] for node in body['nodes']), 1)


class MemoryGraphPrimaryRouterTests(unittest.TestCase):
    native_module = 'memory.ts'
    setUp = MemoryGraphRelayTests.setUp
    create_fixture = MemoryGraphRelayTests.create_fixture
    native_module_name = MemoryGraphRelayTests.native_module_name
    stop_dashboard = MemoryGraphRelayTests.stop_dashboard
    stop_pulse = MemoryGraphRelayTests.stop_pulse
    login = MemoryGraphRelayTests.login
    note = MemoryGraphRelayTests.note
    poison = MemoryGraphRelayTests.poison

    # PULSE dispatches its memory module before the Observability module.
    test_primary_router_preserves_current_owner_graph = (
        MemoryGraphRelayTests.test_owner_graph_renders_registered_notes_and_keeps_cache_unchanged)
    test_primary_router_refuses_ambient_owner = (
        MemoryGraphRelayTests.test_anonymous_graph_read_cannot_borrow_ambient_owner_authority)
    test_primary_router_rechecks_authority_and_connector = (
        MemoryGraphRelayTests.test_revocation_and_connector_loss_refuse_without_raw_cache_fallback)
