# ABOUTME: Verifies governed native wiki collection across memory silos and documentation.
# ABOUTME: Pairs standalone native output with current access, retirement, and physical source tests.
from dataclasses import replace
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_wiki import _files, view
from test_memory_native import OWNER, READER
import test_memory_wiki_render as render_fixture


class MemoryWikiCorpusTests(unittest.TestCase):
    def setUp(self):
        self.fixture = render_fixture.MemoryWikiRenderTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.memory = self.fixture.fixture.fixture.memory

    def source(self, relative, content):
        path = self.root / 'LIFEOS' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def examples(self):
        paths = ['LIFEOS_SYSTEM_PROMPT.md', 'DOCUMENTATION/Overview.md',
            'DOCUMENTATION/Guides/GettingStarted.md', 'ALGORITHM/Steps.md', 'MEMORY/WORK/synthetic-work/ISA.md',
            'MEMORY/LEARNING/SYSTEM/month/synthetic-system.md', 'MEMORY/LEARNING/ALGORITHM/synthetic-algorithm.md',
            'MEMORY/LEARNING/SYNTHESIS/synthetic-synthesis.md', 'MEMORY/WISDOM/FRAMES/synthetic-frame.md',
            'MEMORY/WISDOM/PRINCIPLES/synthetic-principle.md', 'MEMORY/WISDOM/META/synthetic-meta.md',
            'MEMORY/RESEARCH/month/synthetic-research.md']
        return [self.source(path, '# SyntheticPage' + str(index) + '\nSyntheticCorpusMarker' + str(index) + '\n')
                for index, path in enumerate(paths)]

    def test_managed_categories_slugs_and_groups_match_native_standalone(self):
        self.assert_native_sources(self.examples())

    def assert_native_sources(self, paths):
        managed = view(self.memory, OWNER, '/api/wiki')
        graph = view(self.memory, OWNER, '/api/wiki/graph')
        self.assertEqual(len(graph['body']['nodes']), len(paths))
        slugs = [node['id'] for node in graph['body']['nodes']]
        managed_bodies = [view(self.memory, OWNER, '/api/wiki/doc/' + slug) for slug in slugs]
        for path in self.fixture.directory.glob('*.md'):
            path.unlink()
        native = self.fixture.call([self.fixture.request('/api/wiki'),
            *[self.fixture.request('/api/wiki/doc/' + slug) for slug in slugs]], standalone=True)
        self.assertEqual([result['status'] for result in managed_bodies], [200] * len(paths))
        for result, control in zip(managed_bodies, native[1:], strict=True):
            actual_time = datetime.fromisoformat(result['body']['lastModified'])
            native_time = datetime.fromisoformat(control['body']['lastModified'].replace('Z', '+00:00'))
            self.assertEqual(int(actual_time.timestamp() * 1000), int(native_time.timestamp() * 1000),
                {'managed': result['body']['lastModified'], 'native': control['body']['lastModified'],
                 'managed_float': actual_time.timestamp(), 'native_float': native_time.timestamp()})
            control['body']['lastModified'] = result['body']['lastModified']
            self.assertEqual(result, control)
        self.assertEqual(managed['body']['tree'], native[0]['body']['tree'])
        self.assertIn('Guides', json.dumps(managed))
        self.assertIn('System', json.dumps(managed))

    def test_source_times_at_millisecond_boundaries_match_native_standalone(self):
        paths = self.examples()
        for index, path in enumerate(paths):
            timestamp = 1790905907387999600 if index % 2 == 0 else 1790905907387999999
            os.utime(path, ns=(timestamp, timestamp))
        self.assert_native_sources(paths)

    def test_retained_silos_and_docs_are_searchable_with_native_excerpt_and_backlinks(self):
        self.source('DOCUMENTATION/Overview.md', '# SyntheticDocTitle\nSyntheticDocBody [[FRAMES--synthetic-frame]]\n')
        self.source('MEMORY/WISDOM/FRAMES/synthetic-frame.md', '# SyntheticWisdomTitle\nSyntheticWisdomBody\n')
        search = view(self.memory, OWNER, '/api/wiki/search?q=SyntheticDocBody')
        self.assertEqual(search['body']['results'][0]['slug'], 'Overview')
        self.assertIn('SyntheticDocBody', search['body']['results'][0]['excerpt'])
        backlinks = view(self.memory, OWNER, '/api/wiki/backlinks/FRAMES--synthetic-frame')
        self.assertEqual(backlinks['body']['backlinks'][0]['slug'], 'Overview')

    def test_hidden_queues_raw_failure_dumps_and_non_native_work_files_are_absent(self):
        paths = ['MEMORY/LEARNING/FAILURES/synthetic.md', 'MEMORY/LEARNING/REFLECTIONS/synthetic.md',
            'MEMORY/WISDOM/FRAMES/_hypotheses/synthetic.md', 'MEMORY/WISDOM/FRAMES/.hidden/synthetic.md',
            'MEMORY/WORK/_private/ISA.md', 'MEMORY/WORK/synthetic/other.md',
            'DOCUMENTATION/_private/synthetic.md', 'DOCUMENTATION/.hidden.md', 'ALGORITHM/nested/synthetic.md']
        for path in paths:
            self.source(path, '# SyntheticExcludedTitle\nSyntheticExcludedBody\n')
        result = view(self.memory, OWNER, '/api/wiki')
        self.assertNotIn('SyntheticExcluded', json.dumps(result))

    def test_every_corpus_requires_unrestricted_current_owner_scope(self):
        self.examples()
        for scope in (READER, replace(OWNER, read=('assistant', 'project')), replace(OWNER, projects=('lab',))):
            with self.subTest(scope=scope):
                with self.assertRaises(MemoryUnavailable):
                    view(self.memory, scope, '/api/wiki')

    def test_source_redirects_cannot_read_other_user_or_system_files(self):
        for relative in ('DOCUMENTATION/synthetic.md', 'MEMORY/RESEARCH/synthetic.md'):
            with self.subTest(relative=relative):
                source = self.source(relative, '# SyntheticAllowed\n')
                target = self.root / 'LIFEOS/USER/CONFIG/synthetic-secret.md'
                target.write_text('SyntheticRedirectBody')
                source.unlink()
                source.symlink_to(target)
                with self.assertRaises(MemoryUnavailable):
                    view(self.memory, OWNER, '/api/wiki')
                source.unlink()

    def test_private_markup_sources_are_excluded_without_changing_raw_files(self):
        paths = [self.source(relative, '# SyntheticPrivateTitle\n<private>SyntheticPrivateBody</private>\n')
                 for relative in ('DOCUMENTATION/private.md', 'MEMORY/WISDOM/META/private.md')]
        result = view(self.memory, OWNER, '/api/wiki')
        self.assertNotIn('SyntheticPrivate', json.dumps(result))
        self.assertTrue(all('SyntheticPrivateBody' in path.read_text() for path in paths))

    def test_correction_retires_older_sources_and_forgotten_claims_in_current_files(self):
        earlier = self.source('DOCUMENTATION/earlier.md', '# SyntheticEarlierTitle\nSyntheticEarlierBody\n')
        os.utime(earlier, (1, 1))
        saved = self.memory.remember(OWNER, category='principal', content='RULE: SyntheticRemovedCorpusClaim',
            title='', project='', request_id='corpus-forget')
        self.assertEqual(self.memory.forget(OWNER, saved['reference'], 'corpus-forgotten')['status'], 'committed')
        removed = self.source('MEMORY/RESEARCH/current.md', '# SyntheticRemovedTitle\nSyntheticRemovedCorpusClaim\n')
        current = self.source('DOCUMENTATION/current.md', '# SyntheticCurrentTitle\nSyntheticCurrentCorpusBody\n')
        result = json.dumps(view(self.memory, OWNER, '/api/wiki'))
        self.assertNotIn('SyntheticEarlierTitle', result)
        self.assertNotIn('SyntheticRemovedTitle', result)
        self.assertIn('SyntheticCurrentTitle', result)
        self.assertIn('SyntheticRemovedCorpusClaim', removed.read_text())
        self.assertTrue(earlier.exists() and current.exists())

    def test_forgotten_filename_labels_do_not_reappear_as_native_fallback_titles(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: Synthetic retired filename',
            title='', project='', request_id='corpus-label')
        self.memory.forget(OWNER, saved['reference'], 'corpus-label-forget')
        self.source('MEMORY/RESEARCH/Synthetic-retired-filename.md', 'Safe body with no heading\n')
        result = view(self.memory, OWNER, '/api/wiki')
        self.assertNotIn('retired', json.dumps(result))

    def test_oversized_source_refuses_before_native_publication(self):
        self.source('DOCUMENTATION/oversized.md', 'x' * (256 * 1024 + 1))
        with self.assertRaisesRegex(MemoryUnavailable, '256 KiB'):
            view(self.memory, OWNER, '/api/wiki')

    def test_invalid_utf8_source_refuses_without_partial_index(self):
        source = self.source('DOCUMENTATION/invalid.md', 'placeholder')
        source.write_bytes(b'\xff')
        with self.assertRaises(MemoryUnavailable):
            view(self.memory, OWNER, '/api/wiki')

    def test_redirected_directory_cannot_supply_an_alias_corpus(self):
        target = self.root / 'LIFEOS/USER/CONFIG'
        (target / 'synthetic.md').write_text('# SyntheticAliasTitle\nSyntheticAliasBody\n')
        directory = self.root / 'LIFEOS/DOCUMENTATION'
        directory.symlink_to(target)
        with self.assertRaises(MemoryUnavailable):
            view(self.memory, OWNER, '/api/wiki')

    def test_aggregate_source_limit_refuses_a_partial_view(self):
        for index in range(13):
            self.source(f'DOCUMENTATION/large-{index}.md', '# SyntheticLarge\n' + 'x' * (256 * 1024 - 32))
        with self.assertRaisesRegex(MemoryUnavailable, 'transport limit'):
            view(self.memory, OWNER, '/api/wiki')

    def test_source_count_limit_bounds_empty_file_and_directory_traversal(self):
        directory = self.root / 'LIFEOS/DOCUMENTATION'
        directory.mkdir()
        for index in range(2049):
            (directory / f'synthetic-{index}.md').touch()
        with self.assertRaisesRegex(MemoryUnavailable, 'count limit'):
            view(self.memory, OWNER, '/api/wiki')

    def test_native_duplicate_slug_between_silos_refuses_ambiguous_pages(self):
        self.source('DOCUMENTATION/synthetic.md', '# SyntheticDoc\n')
        self.source('MEMORY/RESEARCH/synthetic.md', '# SyntheticResearch\n')
        with self.assertRaisesRegex(MemoryUnavailable, 'unique pages'):
            view(self.memory, OWNER, '/api/wiki')

    def test_retired_frontmatter_and_work_directory_labels_are_excluded(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: Synthetic forgotten page label',
            title='', project='', request_id='corpus-frontmatter')
        self.memory.forget(OWNER, saved['reference'], 'corpus-frontmatter-forget')
        self.source('MEMORY/WISDOM/PRINCIPLES/synthetic.md',
            '---\ntitle: Synthetic forgotten page label\ntags: [synthetic]\n---\nSafe body\n')
        self.source('MEMORY/WORK/Synthetic_forgotten_page_label/ISA.md', 'Safe body with no heading\n')
        self.assertNotIn('forgotten', json.dumps(view(self.memory, OWNER, '/api/wiki')))

    def test_markdown_frontmatter_comments_and_rules_remain_native_read_content(self):
        content = '---\ntitle: SyntheticMarkdownTitle\ntags: [synthetic]\n---\n# Native documentation\n' \
                  '<!-- Synthetic documentation comment -->\n---\nSyntheticMarkdownBody\n'
        self.source('DOCUMENTATION/synthetic-markdown.md', content)
        response = view(self.memory, OWNER, '/api/wiki/doc/synthetic-markdown')
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['body']['content'], content)
        self.assertEqual(response['body']['title'], 'SyntheticMarkdownTitle')

    def test_read_content_can_exceed_native_write_limit_without_changing_that_limit(self):
        content = '# SyntheticLargeReadTitle\n' + ('Synthetic documentation words\n' * 3000)
        self.source('DOCUMENTATION/synthetic-large-read.md', content)
        response = view(self.memory, OWNER, '/api/wiki/doc/synthetic-large-read')
        self.assertEqual(response['status'], 200)
        self.assertEqual(response['body']['content'], content)
        rejected = self.memory.remember(OWNER, category='project', content=content,
            title='SyntheticTooLargeWrite', project='lab', request_id='native-write-limit')
        self.assertEqual(rejected['status'], 'rejected')
        self.assertIn('size limit', rejected['reason'])

    def test_malformed_private_openers_and_canonical_control_characters_are_excluded(self):
        for index, content in enumerate(('Safe prefix <private SyntheticPrivateRemainder',
                'Safe prefix <pr\u200bivate>SyntheticPrivateRemainder', 'Safe prefix \u0085SyntheticControlBody')):
            self.source(f'DOCUMENTATION/invalid-{index}.md', content)
        response = view(self.memory, OWNER, '/api/wiki')
        self.assertNotIn('SyntheticPrivate', json.dumps(response))
        self.assertNotIn('SyntheticControl', json.dumps(response))

    def test_private_source_names_and_groups_cannot_supply_page_metadata(self):
        paths = ('DOCUMENTATION/<private>SyntheticPrivateFilename.md',
                 'DOCUMENTATION/<private>SyntheticPrivateGroup/safe.md',
                 'MEMORY/WORK/<pr\u200bivate>SyntheticPrivateWork/ISA.md',
                 'MEMORY/WISDOM/FRAMES/Synthetic\u0085ControlFilename.md')
        for relative in paths:
            self.source(relative, 'Safe body without a title\n')
        result = json.dumps(view(self.memory, OWNER, '/api/wiki'))
        self.assertNotIn('SyntheticPrivate', result)
        self.assertNotIn('ControlFilename', result)
        self.assertTrue(all((self.root / 'LIFEOS' / relative).exists() for relative in paths))

    def test_hidden_population_counts_toward_directory_scan_limit(self):
        directory = self.root / 'LIFEOS/DOCUMENTATION'
        directory.mkdir()
        for index in range(2049):
            (directory / f'.hidden-{index}').touch()
        with self.assertRaisesRegex(MemoryUnavailable, 'count limit'):
            view(self.memory, OWNER, '/api/wiki')

    def test_non_source_work_population_counts_toward_directory_scan_limit(self):
        directory = self.root / 'LIFEOS/MEMORY/WORK'
        directory.mkdir()
        for index in range(2049):
            (directory / f'unrelated-{index}.txt').touch()
        with self.assertRaisesRegex(MemoryUnavailable, 'count limit'):
            view(self.memory, OWNER, '/api/wiki')

    def test_directory_scan_stops_before_materializing_oversized_population(self):
        directory = self.root / 'LIFEOS/DOCUMENTATION'
        directory.mkdir()
        for index in range(4096):
            (directory / f'unrelated-{index}.txt').touch()
        original = os.scandir
        consumed = []

        @contextmanager
        def observed(path):
            with original(path) as entries:
                def counted():
                    for entry in entries:
                        consumed.append(entry.name)
                        yield entry
                yield counted()

        with patch.object(os, 'scandir', observed):
            with self.assertRaisesRegex(MemoryUnavailable, 'count limit'):
                _files(directory)
        self.assertEqual(len(consumed), 2049)

    def test_directory_scan_budget_is_shared_between_retained_silos(self):
        for relative in ('DOCUMENTATION', 'MEMORY/WORK'):
            directory = self.root / 'LIFEOS' / relative
            directory.mkdir()
            for index in range(1025):
                (directory / f'unrelated-{index}.txt').touch()
        with self.assertRaisesRegex(MemoryUnavailable, 'count limit'):
            view(self.memory, OWNER, '/api/wiki')


if __name__ == '__main__':
    unittest.main()
