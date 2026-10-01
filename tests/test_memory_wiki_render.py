# ABOUTME: Verifies native wiki rendering uses declared sources without raw body reads.
# ABOUTME: Tests native standalone controls and current corpus replacement in real Bun.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import SOURCE


class MemoryWikiRenderTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        (self.root / 'LIFEOS/PULSE').symlink_to(SOURCE / 'LIFEOS/PULSE')
        self.directory = self.root / 'LIFEOS/MEMORY/KNOWLEDGE/Research'
        self.directory.mkdir(parents=True)
        self.note = self.directory / 'synthetic-wiki-current.md'
        self.note.write_text('---\ntitle: SyntheticDeclaredWikiTitle\nquality: 4\ntags: [synthetic]\n'
                             'related: [synthetic-wiki-linked]\n---\nSyntheticRawWikiBodyMarker\n')
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.current = {'path': str(self.note), 'content': self.note.read_text().replace(
            'SyntheticRawWikiBodyMarker', 'SyntheticDeclaredWikiBodyMarker [[synthetic-wiki-linked]]'),
            'lastModified': self.timestamp, 'category': 'research', 'slug': self.note.stem}
        linked = self.directory / 'synthetic-wiki-linked.md'
        linked.write_text('---\ntitle: SyntheticLinkedWikiTitle\n---\nSynthetic linked body\n')
        self.linked = {'path': str(linked), 'content': linked.read_text(), 'lastModified': self.timestamp,
                       'category': 'research', 'slug': linked.stem}
        self.unknown = self.directory / 'synthetic-wiki-unknown.md'
        self.unknown.write_text('---\ntitle: SyntheticUnknownWikiTitle\n---\nSyntheticUnknownWikiBodyMarker\n')

    def call(self, requests, *, standalone=False):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if standalone:
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = subprocess.run(['bun', '--no-install', str(Path(__file__).with_name('native_memory_wiki.ts')),
            str(self.root / 'LIFEOS/PULSE/modules/wiki.ts')], input=json.dumps({'standalone': standalone,
                'requests': requests}), env=environment, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def request(self, path, sources=None):
        return {'path': path, 'sources': [self.current, self.linked] if sources is None else sources}

    def test_standalone_wiki_keeps_native_index_search_and_raw_note_control(self):
        result = self.call([self.request('/api/wiki'), self.request('/api/wiki/search?q=SyntheticRawWikiBodyMarker'),
            self.request('/api/wiki/knowledge/research/' + self.note.stem)], standalone=True)
        self.assertIn('SyntheticUnknownWikiTitle', json.dumps(result[0]))
        self.assertIn('SyntheticRawWikiBodyMarker', json.dumps(result[1]))
        self.assertEqual(result[2]['body']['content'], self.note.read_text())

    def test_supplied_native_note_body_search_and_excerpt_never_read_raw_body(self):
        result = self.call([self.request('/api/wiki/knowledge/research/' + self.note.stem),
            self.request('/api/wiki/doc/' + self.note.stem),
            self.request('/api/wiki/search?q=SyntheticDeclaredWikiBodyMarker')])
        self.assertEqual(result[0]['body']['content'], self.current['content'])
        self.assertEqual(result[1]['body']['content'], self.current['content'])
        self.assertIn('SyntheticDeclaredWikiBodyMarker', json.dumps(result[2]))
        self.assertNotIn('SyntheticRawWikiBodyMarker', json.dumps(result))
        self.assertEqual(result[0]['body']['lastModified'], self.timestamp)
        self.assertEqual(result[0]['body']['tags'], ['synthetic'])
        self.assertEqual(result[0]['body']['quality'], 4)

    def test_supplied_index_graph_and_backlinks_exclude_raw_unknown_sources(self):
        result = self.call([self.request('/api/wiki'), self.request('/api/wiki/graph'),
            self.request('/api/wiki/backlinks/' + self.linked['slug'])])
        self.assertNotIn('SyntheticUnknownWikiTitle', json.dumps(result))
        self.assertEqual(len(result[1]['body']['nodes']), 2)
        self.assertEqual(result[1]['body']['edges'], [{'source': self.current['slug'], 'target': self.linked['slug']}])
        self.assertEqual(result[2]['body']['backlinks'][0]['slug'], self.current['slug'])

    def test_empty_later_corpus_cannot_reuse_previous_search_or_index(self):
        result = self.call([self.request('/api/wiki/search?q=SyntheticDeclaredWikiBodyMarker'),
            self.request('/api/wiki/search?q=SyntheticDeclaredWikiBodyMarker', []),
            self.request('/api/wiki/graph', []), self.request('/api/wiki', [])])
        self.assertTrue(result[0]['body']['results'])
        self.assertEqual(result[1]['body']['results'], [])
        self.assertEqual(result[2]['body'], {'nodes': [], 'edges': []})
        self.assertNotIn('SyntheticDeclaredWikiTitle', json.dumps(result[3]))

    def test_missing_declared_note_has_native_not_found_result(self):
        result = self.call([self.request('/api/wiki/knowledge/research/' + self.unknown.stem)])
        self.assertEqual(result[0]['status'], 404)
        self.assertNotIn('SyntheticUnknownWikiBodyMarker', json.dumps(result))

    def test_duplicate_page_slug_refuses_and_does_not_leave_partial_index(self):
        duplicate = {**self.linked, 'slug': self.current['slug']}
        result = self.call([self.request('/api/wiki', [self.current, duplicate]), self.request('/api/wiki/graph', [])])
        self.assertIn('valid unique pages', result[0]['error'])
        self.assertEqual(result[1]['body'], {'nodes': [], 'edges': []})

    def test_duplicate_physical_source_refuses_distinct_slug_aliases(self):
        alias = {**self.current, 'slug': 'synthetic-alias'}
        result = self.call([self.request('/api/wiki', [self.current, alias])])
        self.assertIn('valid unique pages', result[0]['error'])

    def test_declared_renderer_does_not_scan_or_stat_another_physical_source(self):
        source = {**self.current, 'path': str(self.fixture.fixture.home / 'synthetic-missing-file.md')}
        result = self.call([self.request('/api/wiki/doc/' + self.current['slug'], [source])])
        self.assertEqual(result[0]['body']['content'], self.current['content'])
        self.assertEqual(result[0]['body']['lastModified'], self.timestamp)

    def test_rendering_refuses_write_routes_and_unrelated_module_routes(self):
        result = self.call([{**self.request('/api/wiki/doc/' + self.current['slug']), 'method': 'PUT'},
            self.request('/api/wiki/reindex'), self.request('/api/wiki/skills')])
        self.assertEqual([row['status'] for row in result], [405, 404, 404])


if __name__ == '__main__':
    unittest.main()
