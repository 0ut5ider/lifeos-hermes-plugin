# ABOUTME: Exercises source and generated-text refusals around actual Atlas owner publication.
# ABOUTME: Preserves existing caches when graph identity, links, encoding, or retired text fails admission.
import json
import os
from pathlib import Path
import unittest
import test_memory_atlas_insight as fixture
from test_memory_native import OWNER


class MemoryAtlasInsightEdgeTests(unittest.TestCase):
    setUp = fixture.MemoryAtlasInsightTests.setUp
    seed = fixture.MemoryAtlasInsightTests.seed
    call = fixture.MemoryAtlasInsightTests.call
    prepare = fixture.MemoryAtlasInsightTests.prepare
    value = fixture.MemoryAtlasInsightTests.value

    def test_graph_inode_replacement_invalidates_prepared_generation(self):
        self.seed()
        prepared = self.prepare()
        graph = self.root.parent / '.local/state/lifeos/atlas/atlas.db'
        before = graph.stat()
        replacement = graph.with_name('synthetic-replacement.db')
        replacement.write_bytes(graph.read_bytes())
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        replacement.replace(graph)
        self.assertNotEqual(graph.stat().st_ino, before.st_ino)
        self.assertFalse(self.call('atlas_insight_check', signature=prepared['signature'])['ok'])
        self.assertFalse(self.cache.exists())

    def test_linked_or_invalid_cache_cannot_prepare_or_replace_prior_data(self):
        self.seed()
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        for mode in ('symlink', 'hardlink', 'malformed', 'utf8', 'oversize'):
            with self.subTest(mode=mode):
                self.cache.unlink(missing_ok=True)
                outside = self.owner.fixture.home / 'synthetic-atlas-cache'
                outside.write_text('{"hash":"prior","narrative":"Synthetic prior cache","generated_at":"prior"}')
                if mode == 'symlink': self.cache.symlink_to(outside)
                elif mode == 'hardlink': os.link(outside, self.cache)
                elif mode == 'malformed': self.cache.write_text('{"narrative":')
                elif mode == 'utf8': self.cache.write_bytes(b'{"narrative":"Synthetic prior"}\xff')
                else: self.cache.write_text(' ' * (256 * 1024 + 1))
                before = self.cache.read_bytes()
                result = self.call('atlas_insight_prepare')
                self.assertFalse(result['ok'], result)
                self.assertEqual(self.cache.read_bytes(), before)

    def test_generated_retired_text_cannot_enter_the_private_cache(self):
        self.seed()
        marker = 'SyntheticAtlasRetiredNarrative'
        memory = self.owner.fixture.memory
        saved = memory.remember(OWNER, category='principal', content=marker, title='Synthetic Atlas retirement',
            project='', request_id='atlas-edge-save')
        memory.forget(OWNER, saved['reference'], 'atlas-edge-forget')
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from lifeos_hook_bridge.memory_atlas import DATABASE
        selected = preview(memory, OWNER, [DATABASE])
        self.assertTrue(selected['sources'][0]['accepted'], selected)
        approve(memory, OWNER, [DATABASE], selected['signature'])
        prepared = self.prepare()
        result = self.call('atlas_insight_publish', signature=prepared['signature'],
            value={**self.value(prepared), 'narrative': marker})
        self.assertFalse(result['ok'], result)
        self.assertNotIn(marker, json.dumps(result))
        self.assertFalse(self.cache.exists())

    def test_generated_empty_or_excessive_narrative_and_invalid_timestamp_refuse(self):
        self.seed()
        prepared = self.prepare()
        for change in ({'narrative': ''}, {'narrative': ' '}, {'narrative': 'x' * (256 * 1024)},
                {'generated_at': 'not-a-time'}, {'generated_at': '2026-10-09T12:00:00'}):
            with self.subTest(field=next(iter(change))):
                result = self.call('atlas_insight_publish', signature=prepared['signature'], value={**self.value(prepared), **change})
                self.assertFalse(result['ok'], result)
                self.assertFalse(self.cache.exists())
