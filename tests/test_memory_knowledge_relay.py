# ABOUTME: Tests Observability Knowledge routes against actual Hermes session authentication.
# ABOUTME: Verifies current native notes, standalone controls, retirement, and unsafe write refusal.
import json
import unittest

import httpx

from test_memory_native import OWNER
import test_memory_pulse_relay as relay_fixture
import test_memory_wiki_relay as wiki_fixture


class MemoryKnowledgeRelayTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login
    note = wiki_fixture.MemoryWikiRelayTests.note

    def test_anonymous_index_and_note_cannot_borrow_ambient_owner_metadata(self):
        _, _, note = self.note()
        for route in ('/api/knowledge', '/api/knowledge/research/' + note.stem):
            response = httpx.get(self.native + route, headers={'X-LifeOS-Owner': 'owner'})
            self.assertEqual(response.status_code, 401, response.text)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertNotIn('SyntheticWiki', response.text)

    def test_authenticated_index_and_note_preserve_native_metadata_from_current_sources(self):
        _, _, note = self.note()
        index = note.parent.parent / '_index.md'
        index.write_text('**Last harvest:** SyntheticUnknownHarvestMarker\n')
        with httpx.Client(timeout=20) as client:
            self.login(client)
            response = client.get(self.native + '/api/knowledge')
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body['totalNotes'], 1)
            self.assertEqual(body['notes'][0]['slug'], note.stem)
            self.assertEqual(body['notes'][0]['domain'], 'research')
            self.assertEqual(body['notes'][0]['title'], 'Synthetic lab routing')
            self.assertEqual(body['notes'][0]['quality'], 2)
            self.assertIsNone(body['lastHarvest'])
            self.assertNotIn('SyntheticWikiUnknown', response.text)
            response = client.get(self.native + '/api/knowledge/research/' + note.stem)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('SyntheticWikiCurrentMarker', response.json()['content'])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual(client.get(self.native + '/api/knowledge/research/synthetic-wiki-unknown').status_code, 404)

    def test_correction_and_forget_replace_current_read_shapes_without_deleting_history(self):
        memory, reference, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            route = self.native + '/api/knowledge/research/' + note.stem
            self.assertIn('SyntheticWikiCurrentMarker', client.get(route).text)
            corrected = memory.correct(OWNER, reference, 'SyntheticKnowledgeReplacementMarker', 'knowledge-correct')
            self.assertEqual(corrected['status'], 'committed', corrected)
            response = client.get(route)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('SyntheticKnowledgeReplacementMarker', response.text)
            self.assertNotIn('SyntheticWikiCurrentMarker', response.text)
            self.assertIn('SyntheticWikiCurrentMarker', note.read_text())
            self.assertEqual(memory.forget(OWNER, corrected['reference'], 'knowledge-forget')['status'], 'committed')
            self.assertEqual(client.get(route).status_code, 404)
            index = client.get(self.native + '/api/knowledge')
            self.assertEqual(index.status_code, 200, index.text)
            self.assertEqual(index.json()['totalNotes'], 0)
            self.assertNotIn('SyntheticKnowledgeReplacementMarker', index.text)

    def test_revocation_and_connector_loss_never_return_raw_notes(self):
        _, _, note = self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/knowledge').status_code, 200)
            self.fixture.configuration.update(lambda config: config['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = client.get(self.native + '/api/knowledge/research/' + note.stem)
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('SyntheticWikiCurrentMarker', response.text)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.get(self.native + '/api/knowledge')
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticWikiUnknown', response.text)

    def test_managed_put_refuses_unreviewed_file_replacement(self):
        memory, reference, note = self.note()
        before = note.read_bytes()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            response = client.put(self.native + '/api/knowledge/research/' + note.stem,
                json={'content': 'SyntheticUnreviewedReplacement'})
            self.assertEqual(response.status_code, 405, response.text)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertEqual(note.read_bytes(), before)
        self.assertIn('SyntheticWikiCurrentMarker', memory.get(OWNER, reference)['content'])

    def test_direct_observability_graph_handler_cannot_reopen_raw_cache(self):
        graph = self.root / 'LIFEOS/MEMORY/GRAPH/graph.json'
        graph.parent.mkdir()
        graph.write_text(json.dumps({'generated': '2026-10-01T00:00:00Z', 'nodeCount': 1, 'edgeCount': 0,
            'nodes': [{'id': 'synthetic', 'title': 'SyntheticKnowledgeRawGraphMarker', 'type': 'research',
                'degree': 0, 'tags': [], 'pagerank': 1}], 'edges': []}))
        response = httpx.get(self.native + '/api/memory/graph')
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('SyntheticKnowledgeRawGraphMarker', response.text)

    def test_cross_origin_and_query_parameters_cannot_select_another_source(self):
        self.note()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            response = client.get(self.native + '/api/knowledge', headers={'Origin': 'http://foreign.invalid'})
            self.assertEqual(response.status_code, 403, response.text)
            response = client.get(self.native + '/api/knowledge?root=foreign')
            self.assertEqual(response.status_code, 400, response.text)
            self.assertNotIn('SyntheticWiki', response.text)

    def test_unmanaged_native_control_keeps_raw_index_note_and_write_behavior(self):
        _, _, note = self.note()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.marker.unlink()
        response = httpx.get(self.native + '/api/knowledge')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('SyntheticWikiUnknown', response.text)
        response = httpx.get(self.native + '/api/knowledge/research/' + note.stem)
        self.assertEqual(response.json()['content'], note.read_text())
        response = httpx.put(self.native + '/api/knowledge/research/' + note.stem,
            json={'content': 'SyntheticStandaloneReplacement'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(note.read_text(), 'SyntheticStandaloneReplacement')


if __name__ == '__main__':
    unittest.main()
