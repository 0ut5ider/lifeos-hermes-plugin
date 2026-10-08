# ABOUTME: Exercises native KnowledgeHarvester source mining through a governed owner connector.
# ABOUTME: Checks queue preservation, dry runs, private staging, and retirement policy.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_service import MemoryService
from test_memory_native import OWNER, READER
import unittest

import test_memory_delegation as delegation_fixture


class MemoryKnowledgeHarvestTests(unittest.TestCase):
    def setUp(self):
        self.fixture=delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        self.knowledge=self.root/'LIFEOS/MEMORY/KNOWLEDGE'
        self.queue=self.knowledge/'_harvest-queue/synthetic.json'
        self.queue.parent.mkdir(parents=True)
        self.queue.write_text(json.dumps({'sourcePath':'synthetic-manual-source','title':'Synthetic staged knowledge',
            'content':'Synthetic declared knowledge for source mining.','domain':'Ideas','type':'idea','tags':['synthetic']}))
        self.note=self.queue.parent/'Ideas/synthetic-staged-knowledge.md'
        self.state=self.knowledge/'.harvest-state.json'

    def call(self,*arguments,context=True,managed=True):
        environment=dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        connector=self.root/'LIFEOS/USER/CONFIG/memory-access.json'
        if not managed:connector.unlink()
        return subprocess.run(['bun','--no-install',str(self.root/'LIFEOS/TOOLS/KnowledgeHarvester.ts'),
            'harvest','--source','research',*arguments],env=environment,capture_output=True,text=True,timeout=40)

    def test_unbound_mining_preserves_the_queue_and_state(self):
        before=self.queue.read_bytes()
        result=self.call(context=False)
        self.assertNotEqual(result.returncode,0,result)
        self.assertEqual(self.queue.read_bytes(),before)
        self.assertFalse(self.note.exists())
        self.assertFalse(self.state.exists())

    def test_managed_mining_publishes_private_staging_with_a_receipt(self):
        result=self.call('--request-id','synthetic-harvest')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        receipt=json.loads(result.stdout)['receipt']
        self.assertEqual(receipt['status'],'committed',receipt)
        self.assertEqual(receipt['writer'],'chat-a:100')
        self.assertEqual(receipt['notes_staged'],1)
        self.assertFalse(self.queue.exists())
        self.assertIn('Synthetic declared knowledge',self.note.read_text())
        self.assertEqual(self.note.stat().st_mode&0o777,0o600)
        self.assertEqual(self.state.stat().st_mode&0o777,0o600)
        repeated=self.call('--request-id','synthetic-harvest')
        self.assertEqual(repeated.returncode,0,repeated.stderr)
        self.assertEqual(json.loads(repeated.stdout)['receipt'],receipt)

    def test_revoked_owner_cannot_mine_or_consume_sources(self):
        self.fixture.configuration.update(lambda value:value['accounts'].clear())
        result=self.call()
        self.assertNotEqual(result.returncode,0,result)
        self.assertTrue(self.queue.exists())
        self.assertFalse(self.note.exists())

    def test_read_only_owner_can_preview_but_cannot_stage_sources(self):
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        result=self.call('--dry-run')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Synthetic staged knowledge',result.stdout)
        self.assertTrue(self.queue.exists())
        self.assertFalse(self.note.exists())
        self.assertFalse(self.state.exists())
        self.assertNotEqual(self.call().returncode,0)

    def test_standalone_mining_preserves_native_staging_and_state(self):
        result=self.call(managed=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('1 note(s) staged',result.stdout)
        self.assertFalse(self.queue.exists())
        self.assertIn('Synthetic declared knowledge',self.note.read_text())
        state=json.loads(self.state.read_text())
        self.assertEqual(state['harvestedPaths'],['synthetic-manual-source'])
        self.assertEqual(state['totalHarvested'],0)


    def seed(self,domain='Research',slug='synthetic-seed',body='SyntheticStaleClaimMarker',quality=2,created='2000-01-01',metadata=''):
        path=self.knowledge/domain/(slug+'.md')
        path.parent.mkdir(exist_ok=True)
        path.write_text('---\ntitle: "Synthetic stale seed"\ntype: idea\ndomain: '+domain.lower()+
            '\ncreated: '+created+'\nupdated: '+created+'\nquality: '+str(quality)+'\n'+metadata+'---\n\n# Synthetic stale seed\n\n'+body+'\n')
        with self.fixture.fixture.memory._transaction() as connection:
            reference=self.fixture.fixture.memory._record(connection,OWNER,path,body,'project','lab',{'kind':'synthetic','session':''})
        return path,reference

    def probe(self,mode):
        return subprocess.run([sys.executable,str(Path(__file__).with_name('memory_knowledge_harvest_process.py')),
            str(self.fixture.configuration.path),mode],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))

    def test_expiry_retires_the_fact_and_preserves_its_original_note_bytes(self):
        path,reference=self.seed()
        original=path.read_bytes()
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads(result.stdout)['receipt']
        self.assertEqual(receipt['notes_archived'],1,receipt)
        archive=self.knowledge/'_archive/Research/synthetic-seed.md'
        self.assertEqual(archive.read_bytes(),original)
        self.assertEqual(archive.stat().st_mode&0o777,0o600)
        self.assertFalse(path.exists())
        self.assertEqual(self.fixture.fixture.memory.get(OWNER,reference)['status'],'conflict')
        self.assertEqual(self.fixture.fixture.memory.recall(READER,'SyntheticStaleClaimMarker'),[])
        self.assertTrue(self.fixture.fixture.memory.filter_history(OWNER,'SyntheticStaleClaimMarker','2100-01-01T00:00:00Z')['excluded'])

    def test_expiry_preserves_people_and_company_access_rules(self):
        from dataclasses import replace
        for domain in ('People','Companies'):
            path,reference=self.seed(domain,slug='synthetic-'+domain.lower(),body='SyntheticPrivate'+domain)
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        with self.fixture.fixture.memory._transaction() as connection:
            rows=connection.execute("SELECT * FROM records WHERE status='superseded'").fetchall()
            self.assertEqual(len(rows),2)
            for row in rows:
                self.assertTrue(NativeMemory._private_entity(row['path']))
                self.assertFalse(NativeMemory._allowed(replace(OWNER,read=('project',)),row))

    def test_native_expiry_keeps_referenced_recent_and_high_quality_notes(self):
        referenced,_=self.seed(slug='synthetic-referenced')
        link,_=self.seed(slug='synthetic-link',body='Synthetic backlink [[synthetic-referenced]]',quality=5)
        recent,_=self.seed(slug='synthetic-recent',created='2100-01-01')
        strong,_=self.seed(slug='synthetic-strong',quality=5)
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['receipt']['notes_archived'],0)
        for path in (referenced,link,recent,strong):self.assertTrue(path.exists())

    def test_archive_collision_preserves_every_source(self):
        path,_=self.seed()
        archive=self.knowledge/'_archive/Research/synthetic-seed.md'
        archive.parent.mkdir(parents=True)
        archive.write_text('Synthetic retained archive content')
        before={item:item.read_bytes() for item in (path,archive,self.queue)}
        result=self.call()
        self.assertNotEqual(result.returncode,0)
        for item,content in before.items():self.assertEqual(item.read_bytes(),content)
        self.assertFalse(self.note.exists())

    def test_equal_filenames_in_two_domains_keep_distinct_archives(self):
        first,_=self.seed('Ideas',body='Synthetic first domain claim')
        second,_=self.seed('Research',body='Synthetic second domain claim')
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['receipt']['notes_archived'],2)
        self.assertIn('first domain',(self.knowledge/'_archive/Ideas/synthetic-seed.md').read_text())
        self.assertIn('second domain',(self.knowledge/'_archive/Research/synthetic-seed.md').read_text())

    def test_unregistered_current_notes_are_preserved_and_not_mined(self):
        path,_=self.seed()
        with self.fixture.fixture.memory._transaction() as connection:connection.execute('DELETE FROM records')
        original=path.read_bytes()
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['receipt']['notes_archived'],0)
        self.assertEqual(path.read_bytes(),original)
        self.assertNotIn('Synthetic stale seed',result.stdout)

    def test_forgotten_queue_source_is_withheld_without_consuming_it(self):
        saved=self.fixture.fixture.memory.remember(OWNER,category='project',content='Synthetic retired queue claim',
            title='Synthetic retired queue claim',project='lab',request_id='retired-claim')
        self.fixture.fixture.memory.forget(OWNER,saved['reference'],'forget-claim')
        self.queue.write_text(json.dumps({'title':'Synthetic retired queue claim','content':'Synthetic retired queue claim','domain':'Ideas'}))
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['receipt']['notes_staged'],0)
        self.assertTrue(self.queue.exists())

    def test_native_cap_preserves_unstaged_queue_inputs(self):
        for number in range(8):
            self.queue.with_name('synthetic-'+str(number)+'.json').write_text(json.dumps({
                'title':'Synthetic queue '+str(number),'content':'Synthetic candidate '+str(number),'domain':'Ideas'}))
        result=self.call('--limit','2')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['receipt']['notes_staged'],2)
        self.assertEqual(len(list(self.queue.parent.glob('*.json'))),7)
        self.assertEqual(len(list((self.queue.parent/'Ideas').glob('*.md'))),2)

    def test_same_title_candidates_preserve_the_native_last_candidate_selection(self):
        # Native collection deduplicates before it stages, so equal new titles select the last body.
        self.queue.with_name('zz-synthetic.json').write_text(json.dumps({'title':'Synthetic staged knowledge',
            'content':'Synthetic later same title body','domain':'Ideas'}))
        expected=json.loads(next(path for path in reversed(list(self.queue.parent.iterdir())) if path.suffix=='.json').read_text())['content']
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['receipt']['notes_staged'],1)
        self.assertIn(expected,self.note.read_text())
        self.assertEqual(len(list(self.queue.parent.glob('*.json'))),0)

    def test_legacy_auto_memory_is_not_admitted_in_a_fresh_managed_store(self):
        directory=self.fixture.fixture.home/'.claude/projects/synthetic-legacy/memory'
        directory.mkdir(parents=True)
        (directory/'synthetic-legacy.md').write_text('---\ntype: idea\nname: Synthetic legacy marker\n---\n\nSynthetic legacy body')
        result=self.call('--source','memory')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('Synthetic legacy',result.stdout)
        self.assertFalse((self.queue.parent/'Ideas/synthetic-legacy-marker.md').exists())

    def test_revocation_after_native_render_prevents_every_write(self):
        result=self.probe('authority')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertTrue(self.queue.exists())
        self.assertFalse(self.note.exists())
        self.assertFalse(self.state.exists())

    def test_changed_or_new_sources_after_native_render_preserve_current_inputs(self):
        for mode in ('source','new-source'):
            result=self.probe(mode)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(json.loads(result.stdout)['ok'])
            self.assertTrue(self.queue.exists())
            self.assertFalse(self.note.exists())
            self.assertFalse(self.state.exists())

    def test_interrupted_staging_recovers_sources_registry_and_state(self):
        before=self.queue.read_bytes()
        result=self.probe('interrupt')
        self.assertEqual(result.returncode,73,result.stderr)
        self.assertTrue(self.note.exists())
        self.fixture.fixture.memory.read_hot(OWNER,'principal')
        self.assertEqual(self.queue.read_bytes(),before)
        self.assertFalse(self.note.exists())
        self.assertFalse(self.state.exists())
        retried=self.call('--request-id','synthetic-process-harvest')
        self.assertEqual(retried.returncode,0,retried.stderr)
        self.assertEqual(json.loads(retried.stdout)['receipt']['notes_staged'],1)

    def test_symlink_hardlink_and_group_writable_queue_sources_are_refused(self):
        original=self.queue.read_bytes()
        other=self.fixture.fixture.home/'synthetic-external.json'
        other.write_bytes(original)
        self.queue.unlink()
        self.queue.symlink_to(other)
        self.assertNotEqual(self.call().returncode,0)
        self.queue.unlink()
        os.link(other,self.queue)
        self.assertNotEqual(self.call().returncode,0)
        self.queue.unlink()
        self.queue.write_bytes(original)
        self.queue.chmod(0o660)
        self.assertNotEqual(self.call().returncode,0)
        self.assertEqual(self.queue.read_bytes(),original)


    def compare_native(self,source,limit):
        before={path:path.read_bytes() for path in self.queue.parent.glob('*.json')}
        managed=self.call('--source',source,'--limit',str(limit))
        self.assertEqual(managed.returncode,0,managed.stderr)
        managed_notes={path.relative_to(self.queue.parent).as_posix():path.read_bytes()
                       for path in self.queue.parent.rglob('*.md')}
        managed_queue={path.name:path.read_bytes() for path in self.queue.parent.glob('*.json')}
        managed_state=json.loads(self.state.read_text())
        for path in self.queue.parent.rglob('*.md'):path.unlink()
        for path in self.queue.parent.glob('*.json'):path.unlink()
        for path,content in reversed(list(before.items())):path.write_bytes(content)
        restored=[path for path in self.queue.parent.iterdir() if path.suffix=='.json']
        if restored != list(before):
            for path in restored:path.unlink()
            for path,content in before.items():path.write_bytes(content)
        self.assertEqual([path for path in self.queue.parent.iterdir() if path.suffix=='.json'],list(before),
                         'The native comparison requires identical filesystem candidate order')
        self.state.unlink()
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        tools=self.root/'LIFEOS/TOOLS'
        tools.unlink()
        control=Path(os.environ.get('LIFEOS_HARVEST_CONTROL_SOURCE',str(Path.home()/
            '.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install')))
        tools.symlink_to(control/'LIFEOS/TOOLS')
        standalone=self.call('--source',source,'--limit',str(limit),context=False)
        self.assertEqual(standalone.returncode,0,standalone.stderr)
        native_notes={path.relative_to(self.queue.parent).as_posix():path.read_bytes()
                      for path in self.queue.parent.rglob('*.md')}
        self.assertEqual(managed_notes,native_notes)
        self.assertEqual(managed_queue,{path.name:path.read_bytes() for path in self.queue.parent.glob('*.json')})
        native_state=json.loads(self.state.read_text())
        for state in (managed_state,native_state):state.pop('lastHarvest')
        self.assertEqual(managed_state,native_state)
        self.assertEqual(json.loads(managed.stdout)['receipt']['stdout'],standalone.stdout)

    def test_queue_cap_matches_the_pinned_original_native_command(self):
        for number in range(8):
            self.queue.with_name('synthetic-'+str(number)+'.json').write_text(json.dumps({
                'title':'Synthetic queue '+str(number),'content':'Synthetic candidate '+str(number),'domain':'Ideas'}))
        self.compare_native('research',2)

    def test_work_source_parsing_matches_the_pinned_original_native_command(self):
        directory=self.root/'LIFEOS/MEMORY/WORK/20261008-100000_synthetic-task'
        directory.mkdir(parents=True)
        (directory/'ISA.md').write_text('---\nphase: complete\ntask: Synthetic completed work\n---\n\n'
            '## Decisions\n\nSynthetic declared work decision.\n\n## Verification\n\nSynthetic verification result.\n')
        self.compare_native('work',5)

    def test_research_source_parsing_matches_the_pinned_original_native_command(self):
        directory=self.root/'LIFEOS/MEMORY/RESEARCH/synthetic-topic'
        directory.mkdir(parents=True)
        (directory/'synthetic-research.md').write_text('# Synthetic measured research\n\n'+
            'Synthetic observation with a repeatable method and concrete evidence. '*8)
        (directory/'README.md').write_text('Synthetic scaffolding '*20)
        self.compare_native('research',5)


    def test_interrupted_expiry_restores_the_note_and_active_registry(self):
        path,reference=self.seed()
        before=path.read_bytes()
        result=self.probe('interrupt-expiry')
        self.assertEqual(result.returncode,73,result.stderr)
        self.assertFalse(path.exists())
        self.fixture.fixture.memory.read_hot(OWNER,'principal')
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(self.fixture.fixture.memory.get(OWNER,reference)['status'],'ok')
        self.assertFalse((self.knowledge/'_archive/Research/synthetic-seed.md').exists())
        self.assertTrue(self.queue.exists())
        self.assertFalse(self.note.exists())

    def test_expired_registry_and_archive_pass_native_backup_integrity(self):
        from lifeos_hook_bridge.memory_backup import create,inspect
        self.seed()
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        destination=self.fixture.fixture.home/'synthetic-expiry-backup'
        manifest=create(self.fixture.fixture.memory,OWNER,destination)
        inspected=inspect(self.fixture.fixture.memory,OWNER,destination,manifest['signature'])
        self.assertIn('MEMORY/KNOWLEDGE/_archive/Research/synthetic-seed.md',
                      [item['path'] for item in inspected['files']])

    def test_unregistered_same_title_blocks_replacement_without_exposing_its_body(self):
        path,_=self.seed('Ideas',slug='synthetic-staged-knowledge',body='Synthetic unregistered private body')
        with self.fixture.fixture.memory._transaction() as connection:connection.execute('DELETE FROM records')
        before=path.read_bytes()
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['receipt']['notes_staged'],0)
        self.assertTrue(self.queue.exists())
        self.assertFalse(self.note.exists())
        self.assertEqual(path.read_bytes(),before)
        self.assertNotIn('Synthetic unregistered private body',result.stdout)

    def test_queue_domain_cannot_select_another_publication_path(self):
        self.queue.write_text(json.dumps({'title':'Synthetic invalid domain','content':'Synthetic body','domain':'../../outside'}))
        before=self.queue.read_bytes()
        result=self.call()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.queue.read_bytes(),before)
        self.assertFalse(self.state.exists())


    def test_retry_cannot_return_a_later_forgotten_source_label(self):
        result=self.call('--request-id','synthetic-retired-retry')
        self.assertEqual(result.returncode,0,result.stderr)
        saved=self.fixture.fixture.memory.remember(OWNER,category='project',content='synthetic staged knowledge',
            title='Synthetic retirement receipt control',project='lab',request_id='retired-receipt-control')
        self.assertEqual(saved['status'],'committed',saved)
        forgotten=self.fixture.fixture.memory.forget(OWNER,saved['reference'],'forget-receipt-label')
        self.assertEqual(forgotten['status'],'committed',forgotten)
        retried=self.call('--request-id','synthetic-retired-retry')
        self.assertNotEqual(retried.returncode,0)
        self.assertNotIn('synthetic-staged-knowledge',retried.stdout)
        self.assertNotIn('synthetic staged knowledge',retried.stdout.casefold())


if __name__=='__main__':
    unittest.main()
