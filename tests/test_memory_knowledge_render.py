# ABOUTME: Tests native Knowledge index and body shapes from declared source content.
# ABOUTME: Verifies source isolation, metadata, path refusal, and fixed route admission with real Bun.
import json
import os
from pathlib import Path
import subprocess
import unittest

from lifeos_hook_bridge.memory_knowledge import request_target
import test_memory_wiki_render as render_fixture


class MemoryKnowledgeRenderTests(unittest.TestCase):
    def setUp(self):
        self.fixture = render_fixture.MemoryWikiRenderTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.source = {'path': str(self.fixture.note), 'content': self.fixture.current['content']}
        self.route = '/api/knowledge/research/' + self.fixture.note.stem

    def call(self, requests, *, standalone=False):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if standalone:
            (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = subprocess.run(['bun', '--no-install', str(Path(__file__).with_name('native_memory_knowledge.ts')),
            str(self.fixture.root / 'LIFEOS/PULSE/Observability/observability.ts')],
            input=json.dumps({'requests': requests, 'standalone': standalone}), env=environment,
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_declared_index_and_body_match_native_standalone_for_the_same_sources(self):
        sources = [{'path': str(path), 'content': path.read_text()} for path in sorted(self.fixture.directory.glob('*.md'))]
        requests = [self.request('/api/knowledge', sources), self.request(self.route, sources)]
        managed = self.call(requests)
        standalone = self.call(requests, standalone=True)
        # Equal update dates retain the input order, which is not a filesystem ordering contract.
        for response in (managed[0], standalone[0]):
            response['body']['notes'].sort(key=lambda note: note['slug'])
        self.assertEqual(managed, standalone)

    def request(self, path, sources=None):
        return {'path': path, 'sources': [self.source] if sources is None else sources}

    def test_native_declared_index_uses_source_metadata_without_raw_unknown_note(self):
        index = self.fixture.directory.parent / '_index.md'
        index.write_text('**Last harvest:** SyntheticRawHarvestMarker\n')
        result = self.call([self.request('/api/knowledge')])[0]
        self.assertEqual(result['status'], 200)
        self.assertEqual(result['body']['totalNotes'], 1)
        self.assertEqual(result['body']['avgQuality'], 4)
        self.assertEqual(result['body']['notes'][0]['title'], 'SyntheticDeclaredWikiTitle')
        self.assertEqual(result['body']['topTags'], [{'tag': 'synthetic', 'count': 1}])
        self.assertEqual(result['body']['domains'][-1], {'name': 'Research', 'count': 1, 'avgQuality': 4,
            'lowCount': 0, 'midCount': 1, 'highCount': 0})
        self.assertIsNone(result['body']['lastHarvest'])
        self.assertNotIn('SyntheticRawHarvestMarker', json.dumps(result))
        self.assertNotIn('SyntheticUnknownWiki', json.dumps(result))

    def test_native_declared_body_does_not_reopen_raw_note_text(self):
        result = self.call([self.request(self.route)])[0]
        self.assertEqual(result['status'], 200)
        self.assertEqual(result['body']['content'], self.source['content'])
        self.assertNotIn('SyntheticRawWikiBodyMarker', json.dumps(result))

    def test_later_empty_corpus_cannot_reuse_prior_notes_or_index(self):
        result = self.call([self.request(self.route), self.request(self.route, []), self.request('/api/knowledge', [])])
        self.assertEqual([row['status'] for row in result], [200, 404, 200])
        self.assertEqual(result[-1]['body']['totalNotes'], 0)
        self.assertNotIn('SyntheticDeclaredWiki', json.dumps(result[1:]))

    def test_declared_source_needs_no_physical_note_or_directory_stat(self):
        source = {**self.source, 'path': str(self.fixture.directory / 'synthetic-missing.md')}
        result = self.call([self.request('/api/knowledge/research/synthetic-missing', [source])])[0]
        self.assertEqual(result['status'], 200)
        self.assertEqual(result['body']['content'], self.source['content'])

    def test_duplicate_and_foreign_sources_refuse_without_partial_index(self):
        foreign = {**self.source, 'path': str(self.fixture.root / 'LIFEOS/USER/CONFIG/synthetic.md')}
        result = self.call([self.request('/api/knowledge', [self.source, self.source]),
            self.request('/api/knowledge', [foreign]), self.request('/api/knowledge', [])])
        self.assertIn('valid unique native paths', result[0]['error'])
        self.assertIn('valid unique native paths', result[1]['error'])
        self.assertEqual(result[-1]['body']['totalNotes'], 0)

    def test_nonknowledge_and_unknown_routes_do_not_reopen_raw_routes(self):
        result = self.call([self.request('/api/memory/graph'), self.request('/api/knowledge/reindex')])
        self.assertEqual([row['status'] for row in result], [404, 404])

    def test_route_admission_refuses_servers_queries_traversal_and_hidden_names(self):
        self.assertEqual(request_target('/api/knowledge/Research/synthetic-note'), '/api/knowledge/research/synthetic-note')
        for path in ('https://foreign.invalid/api/knowledge', '/api/knowledge?root=foreign',
            '/api/knowledge/research/../synthetic', '/api/knowledge/research/%2e%2e',
            '/api/knowledge/research/_archive', '/api/knowledge/research/synthetic#fragment'):
            with self.subTest(path=path), self.assertRaises((ValueError, LookupError)):
                request_target(path)


if __name__ == '__main__':
    unittest.main()
