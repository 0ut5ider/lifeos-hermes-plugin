# ABOUTME: Exercises native Knowledge status, review, contradictions, and index commands under managed authority.
# ABOUTME: Verifies that retained note labels and derived files cannot bypass current owner grants.
from dataclasses import asdict
import json
import os
import subprocess
import sys
from pathlib import Path

from test_memory_native import OWNER
import unittest
from unittest.mock import patch

import test_memory_background_audience as audience_fixture

import test_memory_knowledge_harvest as harvest_fixture


class MemoryKnowledgeViewTests(unittest.TestCase):
    def setUp(self):
        self.harvest=harvest_fixture.MemoryKnowledgeHarvestTests()
        self.harvest.setUp()
        self.addCleanup(self.harvest.doCleanups)
        self.fixture=self.harvest.fixture
        self.root=self.fixture.root
        self.knowledge=self.harvest.knowledge
        self.first,_=self.harvest.seed(slug='synthetic-view-first',body='Synthetic first view fact',quality=5,
            metadata='tags: [synthetic, overlap, test]\n')
        self.second,_=self.harvest.seed(slug='synthetic-view-second',body='Synthetic second view fact [[missing-target]]',quality=5,
            metadata='tags: [synthetic, overlap, test]\n')
        self.staged=self.knowledge/'_harvest-queue/Ideas/synthetic-view-staged.md'
        self.staged.parent.mkdir(parents=True)
        self.staged.write_text('---\ntitle: "Synthetic private staging title"\ntype: idea\ndomain: ideas\n'
            'created: 2026-10-01\nquality: 5\nstatus: pending-review\nharvested_from: synthetic-private-source.md\n---\n\n'
            '# Synthetic private staging title\n\nSynthetic pending review body\n')

    def call(self,command,*,context=True):
        environment=dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),
                         BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun','--no-install',str(self.root/'LIFEOS/TOOLS/KnowledgeHarvester.ts'),command],
                              capture_output=True,text=True,env=environment,timeout=40)

    def test_unbound_views_do_not_expose_source_labels_or_publish_indexes(self):
        for command in ('review','status','contradictions','index'):
            with self.subTest(command=command):
                result=self.call(command,context=False)
                self.assertNotEqual(result.returncode,0,result)
                self.assertNotIn('Synthetic private staging title',result.stdout+result.stderr)
                self.assertNotIn('missing-target',result.stdout+result.stderr)
                self.assertFalse((self.knowledge/'_index.md').exists())
                self.assertFalse((self.knowledge/'Research/_index.md').exists())

    def test_owner_can_read_each_native_view(self):
        for command,marker in [('review','Synthetic private staging title'),('status','Total notes: 2'),
                               ('contradictions','synthetic-view-first')]:
            with self.subTest(command=command):
                result=self.call(command)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stderr,'')
                self.assertIn(marker,json.loads(result.stdout)['stdout'])

    def test_read_only_owner_cannot_regenerate_indexes(self):
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        result=self.call('index')
        self.assertNotEqual(result.returncode,0,result)
        self.assertFalse((self.knowledge/'_index.md').exists())

    def test_owner_index_returns_a_private_governed_publication(self):
        result=self.call('index')
        self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads(result.stdout)['receipt']
        self.assertEqual(receipt['status'],'committed',receipt)
        self.assertEqual(receipt['writer'],'chat-a:100')
        self.assertEqual(receipt['indexes_published'],5)
        self.assertIn('synthetic-view-first',(self.knowledge/'Research/_index.md').read_text())
        for path in [self.knowledge/'_index.md',*[self.knowledge/domain/'_index.md' for domain in ('People','Companies','Ideas','Research')]]:
            self.assertEqual(path.stat().st_mode&0o777,0o600)


    def probe(self,mode,view):
        return subprocess.run([sys.executable,str(Path(__file__).with_name('memory_knowledge_views_process.py')),
            str(self.fixture.configuration.path),mode,view],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))

    def test_revoked_owner_cannot_read_the_staging_queue(self):
        self.fixture.configuration.update(lambda value:value['accounts'].clear())
        result=self.call('review')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Synthetic private staging title',result.stdout+result.stderr)

    def test_forgotten_staging_metadata_is_excluded(self):
        saved=self.fixture.fixture.memory.remember(OWNER,category='project',content='Synthetic private staging title',
            title='Synthetic retired view control',project='lab',request_id='retired-view-control')
        self.fixture.fixture.memory.forget(OWNER,saved['reference'],'forget-view-control')
        result=self.call('review')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('Synthetic private staging title',result.stdout)
        self.assertIn('Queue is empty',json.loads(result.stdout)['stdout'])
        self.assertTrue(self.staged.exists())

    def test_unregistered_note_labels_do_not_appear_in_views_or_indexes(self):
        with self.fixture.fixture.memory._transaction() as connection:
            connection.execute('DELETE FROM records WHERE path=?',(self.second.relative_to(self.root).as_posix(),))
        for view in ('status','contradictions','index'):
            result=self.call(view)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('missing-target',result.stdout)
        self.assertNotIn('synthetic-view-second',(self.knowledge/'Research/_index.md').read_text())

    def test_current_authority_is_required_after_every_native_view_render(self):
        for view in ('review','status','contradictions','index'):
            with self.subTest(view=view):
                result=self.probe('authority',view)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertFalse((self.knowledge/'_index.md').exists())
                self.fixture.configuration.update(lambda value:value['accounts'].update({'chat-a:100':'owner'}))

    def test_source_changes_refuse_read_results_and_index_publication(self):
        before=self.first.read_text()
        for view in ('status','index'):
            result=self.probe('source',view)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(json.loads(result.stdout)['ok'])
            self.assertIn('Synthetic concurrent source edit',self.first.read_text())
            self.assertFalse((self.knowledge/'_index.md').exists())
            self.first.write_text(before)

    def test_interrupted_index_publication_restores_the_complete_index_set(self):
        indexes=[self.knowledge/'_index.md',*[self.knowledge/domain/'_index.md' for domain in ('People','Companies','Ideas','Research')]]
        for path in indexes:
            path.parent.mkdir(exist_ok=True)
            path.write_text('Synthetic original index '+path.parent.name+'\n')
        before={path:path.read_bytes() for path in indexes}
        result=self.probe('interrupt','index')
        self.assertEqual(result.returncode,73,result.stderr)
        self.assertNotEqual({path:path.read_bytes() for path in indexes},before)
        self.fixture.fixture.memory.read_hot(OWNER,'principal')
        self.assertEqual({path:path.read_bytes() for path in indexes},before)

    def test_native_read_views_match_the_pinned_original_command(self):
        control=Path(os.environ.get('LIFEOS_HARVEST_CONTROL_SOURCE',str(Path.home()/
            '.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install')))
        environment=dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'))
        for view in ('review','status','contradictions'):
            managed=self.call(view)
            self.assertEqual(managed.returncode,0,managed.stderr)
            standalone=subprocess.run(['bun','--no-install',str(control/'LIFEOS/TOOLS/KnowledgeHarvester.ts'),view],
                capture_output=True,text=True,timeout=30,env=environment)
            self.assertEqual(standalone.returncode,0,standalone.stderr)
            self.assertEqual(json.loads(managed.stdout)['stdout'],standalone.stdout)

    def test_standalone_index_keeps_its_native_behavior(self):
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result=self.call('index',context=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Regenerating all MOC',result.stdout)
        self.assertIn('synthetic-view-first',(self.knowledge/'Research/_index.md').read_text())


class MemoryKnowledgeViewAudienceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=audience_fixture.MemoryBackgroundAudienceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        staged=self.fixture.root/'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue/Ideas/synthetic-private-view.md'
        staged.parent.mkdir(parents=True)
        staged.write_text('---\ntitle: "Synthetic private audience view"\ntype: idea\ndomain: ideas\n'
            'created: 2026-10-08\nquality: 5\nharvested_from: synthetic-source\n---\n\nSynthetic private view body\n')

    def test_read_views_require_the_current_audience_after_final_source_check(self):
        import lifeos_hook_bridge.memory_knowledge_views as module
        original=module._snapshot
        calls=0
        def observe(memory):
            nonlocal calls
            result=original(memory)
            calls+=1
            if calls==2:self.fixture.open_channel()
            return result
        with patch.object(module,'_snapshot',observe):
            result=self.fixture.service.native(self.fixture.context,'knowledge_view',
                {'view':'review','request_id':'audience-final-view'})
        self.assertTrue(self.fixture.changed,'The test must finish native rendering and source checks')
        self.assertFalse(result.get('ok'),result)
        self.assertNotIn('stdout',result)
        self.assertIn('/channels/60',self.fixture.audience.requests)


if __name__=='__main__':
    unittest.main()
