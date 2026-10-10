# ABOUTME: Changes real HTTP channel permissions after native background source processing.
# ABOUTME: Verifies reads and publication stop when the admitted Discord audience changes.
import copy
from datetime import datetime, timezone
import json
from unittest.mock import patch
import unittest

from lifeos_hook_bridge.discord_audience import DiscordAPI, resolve_audience
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
import test_discord_audience as audience_fixture
import test_memory_native as native_fixture


class MemoryBackgroundAudienceTests(unittest.TestCase):
    def setUp(self):
        self.audience = audience_fixture.DiscordAudienceTests()
        self.audience.setUp()
        self.addCleanup(self.audience.doCleanups)
        self.fixture = native_fixture.NativeMemoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.memory_root = self.root / 'LIFEOS/MEMORY'
        configuration = copy.deepcopy(self.audience.configuration)
        configuration.update(root=str(self.root), ownership_enabled=True, sharing_enabled=False, clients={})
        configuration['destinations']['discord:60'].update(
            write=['principal','assistant','project'], projects=['*'])
        self.configuration = MemoryConfiguration(self.fixture.home / 'memory.json')
        self.configuration.save(configuration)
        self.context = self.audience.context()
        api = DiscordAPI('synthetic-token', origin=self.audience.origin)
        self.service = MemoryService(self.configuration,
            audience_lookup=lambda configuration, metadata: resolve_audience(configuration, metadata, api=api))
        self.stamp = datetime.now(timezone.utc).isoformat()
        self.ratings = self.memory_root / 'LEARNING/SIGNALS/ratings.jsonl'
        self.ratings.parent.mkdir(parents=True)
        self.ratings.write_text(''.join(json.dumps({'timestamp':self.stamp, 'rating':8,
            'session_id':'synthetic-'+str(n), 'source':'explicit', 'confidence':1,
            'sentiment_summary':'Well done on synthetic verification'})+'\n' for n in range(8)))
        self.frames = self.memory_root / 'WISDOM/FRAMES'
        self.frames.mkdir(parents=True)
        content = ('# Synthetic frame\n## Meta\n- **Confidence:** 70%\n- **Observation Count:** 12\n'
            '- **Last Crystallized:** 2026-10-01\n\n## Core Principles\n'
            '### Synthetic concrete verification principle [CRYSTAL]\n')
        for name in ('communication', 'development'):
            (self.frames / (name+'.md')).write_text(content)
        stream = self.memory_root / 'OBSERVABILITY/tool-failures.jsonl'
        stream.parent.mkdir(parents=True)
        stream.write_text(json.dumps({'timestamp':self.stamp, 'event':'tool_failure', 'tool_name':'terminal',
            'error':'Synthetic recurrence failure', 'session_id':'synthetic'})+'\n')
        with self.fixture.memory._transaction():
            pass
        self.changed = False

    def open_channel(self):
        if not self.changed:
            self.audience.responses['/channels/60']['permission_overwrites'].append(
                {'id':'40','type':1,'allow':'1024','deny':'0'})
            self.changed = True

    def snapshot(self):
        return {str(path.relative_to(self.memory_root)):path.read_bytes()
            for path in self.memory_root.rglob('*') if path.is_file()
            and not (path.parent.name == 'STATE' and path.name.startswith('memory-access.sqlite'))}

    def arguments(self, operation):
        base = str(self.root / 'LIFEOS')
        if operation == 'learning_hypotheses':
            return dict(path=str(self.ratings), window=7, dry_run=False, no_inference=True,
                once_daily=False, request_id='audience-hypotheses')
        if operation == 'learning_ratings':
            return dict(path=str(self.ratings), month=False, all=True, dry_run=False, request_id='audience-ratings')
        if operation in ('recurrence_sources','wisdom_frames'):
            return dict(base=base)
        if operation == 'recurrence_append':
            return dict(base=base, record={'ts':self.stamp, 'class_id':'tool:terminal:synthetic',
                'hypothesis_slug':'synthetic', 'files':['hooks/Synthetic.ts'], 'fixture':None,
                'note':'Synthetic repair'}, request_id='audience-append')
        if operation == 'wisdom_synthesis':
            return dict(base=base, health=False, dry_run=False, request_id='audience-synthesis')
        return dict(domain='communication', observation='Synthetic new principle', type='principle',
            path=str(self.frames / 'communication.md'), request_id='audience-update')

    def exercise(self, operation):
        before = self.snapshot()
        if operation in ('recurrence_sources','wisdom_frames'):
            if operation == 'recurrence_sources':
                from lifeos_hook_bridge import memory_recurrence as module
                name = '_collect'
            else:
                from lifeos_hook_bridge import memory_wisdom as module
                name = '_frames'
            original = getattr(module, name)
            def observe(*args, **kwargs):
                result = original(*args, **kwargs)
                self.open_channel()
                return result
            observer = patch.object(module, name, observe)
        else:
            original = NativeMemory._native
            def observe(memory, name, **arguments):
                result = original(memory, name, **arguments)
                if name == operation:
                    self.open_channel()
                return result
            observer = patch.object(NativeMemory, '_native', observe)
        with observer:
            result = self.service.native(self.context, operation, self.arguments(operation))
        self.assertTrue(self.changed, 'The test must reach real native processing')
        self.assertFalse(result.get('ok'), result)
        self.assertNotIn('sources', result)
        self.assertNotIn('stdout', result)
        self.assertEqual(self.snapshot(), before)
        self.assertIn('/channels/60', self.audience.requests)

    def test_hypotheses_recheck_the_current_audience(self):
        self.exercise('learning_hypotheses')

    def test_rating_reports_recheck_the_current_audience(self):
        self.exercise('learning_ratings')

    def test_recurrence_reads_recheck_the_current_audience(self):
        self.exercise('recurrence_sources')

    def test_recurrence_publication_rechecks_the_current_audience(self):
        self.exercise('recurrence_append')

    def test_frame_reads_recheck_the_current_audience(self):
        self.exercise('wisdom_frames')

    def test_wisdom_reports_recheck_the_current_audience(self):
        self.exercise('wisdom_synthesis')

    def test_frame_publication_rechecks_the_current_audience(self):
        self.exercise('wisdom_frame_update')

    def test_unchanged_private_audience_allows_actual_publication(self):
        result = self.service.native(self.context, 'wisdom_frame_update', self.arguments('wisdom_frame_update'))
        self.assertTrue(result.get('ok'), result)
        self.assertIn('Synthetic new principle', (self.frames / 'communication.md').read_text())


if __name__ == '__main__':
    unittest.main()
