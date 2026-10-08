# ABOUTME: Compares native hypothesis review effects with authenticated governed publication.
# ABOUTME: Checks Wisdom frames, archived notes, sidecar updates, refusal, and recovery.
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

import httpx
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_hypothesis_review import review
import test_memory_hypothesis_relay as queue_fixture


class MemoryHypothesisReviewTests(unittest.TestCase):
    native_module='hypotheses.ts'
    setUp=queue_fixture.MemoryHypothesisRelayTests.setUp
    create_fixture=queue_fixture.MemoryHypothesisRelayTests.create_fixture
    native_module_name=queue_fixture.MemoryHypothesisRelayTests.native_module_name
    stop_dashboard=queue_fixture.MemoryHypothesisRelayTests.stop_dashboard
    stop_pulse=queue_fixture.MemoryHypothesisRelayTests.stop_pulse
    login=queue_fixture.MemoryHypothesisRelayTests.login
    seed=queue_fixture.MemoryHypothesisRelayTests.seed

    @property
    def frames(self):return self.root/'LIFEOS/MEMORY/WISDOM/FRAMES'

    def snapshot(self):
        return {path.relative_to(self.frames).as_posix():path.read_text() for path in self.frames.rglob('*') if path.is_file()}

    def reset(self,contents):
        self.frames.mkdir(parents=True,exist_ok=True)
        for path in list(self.frames.iterdir()):
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
        for relative,content in contents.items():
            path=self.frames/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)

    def original(self,verb,note=None,slug='synthetic-hypothesis'):
        control=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        route='/api/hypotheses/'+slug+'/'+verb
        options={'method':'POST','headers':{'content-type':'application/json'},'body':json.dumps({'note':note})}
        script='import {handleRequest} from '+json.dumps(str(control/'LIFEOS/PULSE/modules/hypotheses.ts'))+';'+\
            'const response=await handleRequest(new Request("http://127.0.0.1"+'+json.dumps(route)+','+json.dumps(options)+'),'+json.dumps(route)+');'+\
            'if(!response)throw new Error("Missing native response");console.log(JSON.stringify({status:response.status,body:await response.json()}));'
        result=subprocess.run(['bun','--no-install','-e',script],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,HOME=str(self.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS')))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def normalize(self,value):
        return {key:re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z','SyntheticInstant',content)
                for key,content in value.items()}

    def paired(self,verb,*,existing=False,note=None):
        path=self.seed()
        if existing:
            path.write_text(path.read_text().replace('target_frame: new','target_frame: synthetic-frame'))
            (self.frames/'synthetic-frame.md').write_text('# Frame: Synthetic\n\n## Principles\nSynthetic existing principle\n')
        state=self.frames/'_hypotheses/.state.json'
        state.write_text(json.dumps({'claim_hashes':{'synthetic-hypothesis':{'hash':'synthetic-hash',
            'archived_at':None,'status':'hypothesis'}}}))
        before=self.snapshot()
        expected=self.original(verb,note)
        effects=self.snapshot()
        self.reset(before)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.post(self.native+'/api/hypotheses/synthetic-hypothesis/'+verb,json={'note':note})
            self.assertEqual({'status':response.status_code,'body':response.json()},expected)
            self.assertEqual(self.normalize(self.snapshot()),self.normalize(effects))
            self.assertEqual(response.headers.get('cache-control'),'no-store')

    def test_original_graduation_creates_the_crystallized_frame_and_archives_note(self):
        self.seed()
        result=self.original('graduate')
        self.assertEqual(result['status'],200)
        self.assertIn('[CRYSTAL: 85%]',(self.frames/'synthetic-hypothesis.md').read_text())
        self.assertFalse((self.frames/'_hypotheses/2026-10-08_synthetic-hypothesis.md').exists())
        self.assertIn('status: graduated',(self.frames/'_hypotheses/_archive/2026-10-08_synthetic-hypothesis.md').read_text())

    def test_graduation_new_frame_matches_the_original_effects(self):self.paired('graduate')
    def test_graduation_existing_frame_matches_the_original_effects(self):self.paired('graduate',existing=True,note='Synthetic review note')
    def test_rejection_matches_the_original_archive_and_state_effects(self):self.paired('reject',note='Synthetic rejection note')

    def test_anonymous_mutation_cannot_change_a_hypothesis(self):
        self.seed()
        before=self.snapshot()
        response=httpx.post(self.native+'/api/hypotheses/synthetic-hypothesis/graduate',json={},timeout=20)
        self.assertEqual(response.status_code,401,response.text)
        self.assertEqual(self.snapshot(),before)

    def probe(self,mode):
        return subprocess.run([sys.executable,str(Path(__file__).with_name('memory_hypothesis_review_process.py')),
            str(self.fixture.configuration.path),mode],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))

    def test_source_and_authority_changes_after_render_withhold_publication(self):
        for mode in ('source','authority'):
            with self.subTest(mode=mode):
                path=self.seed()
                result=self.probe(mode)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})
                self.assertTrue(path.exists())
                self.assertFalse((self.frames/'synthetic-hypothesis.md').exists())

    def test_later_frame_archive_and_state_edits_survive_publication_conflicts(self):
        before=self.snapshot()
        for mode in ('frame','archive','state'):
            with self.subTest(mode=mode):
                self.reset(before)
                path=self.seed()
                result=self.probe(mode)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})
                self.assertTrue(path.exists())
                selected={'frame':'synthetic-hypothesis.md','archive':'_hypotheses/_archive/2026-10-08_synthetic-hypothesis.md',
                    'state':'_hypotheses/.state.json'}[mode]
                self.assertIn('later',(self.frames/selected).read_text())

    def test_each_interrupted_publication_restores_the_complete_original_state(self):
        self.seed()
        (self.frames/'_hypotheses/.state.json').write_text(json.dumps({'claim_hashes':{'synthetic-hypothesis':
            {'hash':'synthetic-hash','archived_at':None,'status':'hypothesis'}}}))
        before=self.snapshot()
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        for mode in ('interrupt-frame','interrupt-archive','interrupt-state','interrupt-delete'):
            with self.subTest(mode=mode):
                self.reset(before)
                result=self.probe(mode)
                self.assertEqual(result.returncode,73,result.stderr)
                memory.read_hot(OWNER,'principal')
                self.assertEqual(self.snapshot(),before)

    def test_completed_retry_does_not_duplicate_frame_principles(self):
        self.seed()
        preferences=MemoryPreferences(self.fixture.configuration.path,self.root,Path(sys.executable),
            Path(__file__).resolve().parents[1]/'lifeos_hook_bridge/memory_rpc.py')
        first=preferences.review_hypothesis('/api/hypotheses/synthetic-hypothesis/graduate',None,'synthetic-review-retry',
            account='dashboard:basic:synthetic-owner')
        before=self.snapshot()
        second=preferences.review_hypothesis('/api/hypotheses/synthetic-hypothesis/graduate',None,'synthetic-review-retry',
            account='dashboard:basic:synthetic-owner')
        self.assertEqual(first,second)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual((self.frames/'synthetic-hypothesis.md').read_text().count('[CRYSTAL: 85%]'),1)

    def test_unavailable_target_frame_keeps_the_pending_note(self):
        path=self.seed()
        path.write_text(path.read_text().replace('target_frame: new','target_frame: missing-frame'))
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.post(self.native+'/api/hypotheses/synthetic-hypothesis/graduate',json={})
            self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(self.snapshot(),before)

    def test_original_missing_frame_archives_without_preserving_claim_known_bug(self):
        path=self.seed()
        path.write_text(path.read_text().replace('target_frame: new','target_frame: missing-frame'))
        result=self.original('graduate')
        self.assertEqual(result['status'],200)
        self.assertEqual(result['body']['new_status'],'graduated')
        self.assertFalse(path.exists())
        self.assertFalse((self.frames/'missing-frame.md').exists())
        self.assertIn('status: graduated',(self.frames/'_hypotheses/_archive'/path.name).read_text())

    def test_existing_new_frame_preserves_native_skip_and_archive_effects(self):
        self.seed()
        (self.frames/'synthetic-hypothesis.md').write_text('# Frame: Synthetic retained frame\n\n## Principles\nSynthetic retained principle\n')
        before=self.snapshot()
        expected=self.original('graduate')
        effects=self.snapshot()
        self.reset(before)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.post(self.native+'/api/hypotheses/synthetic-hypothesis/graduate',json={})
            self.assertEqual({'status':response.status_code,'body':response.json()},expected)
        self.assertEqual(self.normalize(self.snapshot()),self.normalize(effects))
        self.assertEqual(self.snapshot()['synthetic-hypothesis.md'],before['synthetic-hypothesis.md'])

    def test_owner_without_approval_authority_cannot_review(self):
        self.seed()
        before=self.snapshot()
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        with self.assertRaises(MemoryUnavailable):
            review(memory,OWNER,target='/api/hypotheses/synthetic-hypothesis/graduate',note=None,
                request_id='synthetic-without-approval')
        self.assertEqual(self.snapshot(),before)

    def test_private_and_control_review_notes_never_enter_archived_sources(self):
        self.seed()
        before=self.snapshot()
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        for note in ('Synthetic\x00review','<private>Synthetic private review</private>'):
            with self.subTest(note=repr(note)):
                self.reset(before)
                with self.assertRaises(MemoryUnavailable):
                    review(memory,replace(OWNER,proposals=('approve',)),
                        target='/api/hypotheses/synthetic-hypothesis/reject',note=note,
                        request_id='synthetic-invalid-review-'+str(len(note)))
                self.assertEqual(self.snapshot(),before)

    def test_registered_note_requires_explicit_fact_review_before_archival(self):
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        marker='RULE: Synthetic retained hypothesis fact'
        saved=memory.remember(OWNER,category='project',content=marker,title='Synthetic hypothesis',
            project='synthetic',request_id='synthetic-hypothesis-registered')
        self.assertEqual(saved['status'],'committed',saved)
        path=self.seed()
        path.write_text(path.read_text()+'\n'+marker+'\n')
        with memory._transaction() as connection:
            connection.execute('UPDATE records SET path=?,position=? WHERE id=?',
                (path.relative_to(self.root).as_posix(),path.read_text().index(marker),saved['reference']['id']))
        self.assertEqual(memory.get(OWNER,saved['reference'])['content'],marker)
        before=self.snapshot()
        with self.assertRaises(MemoryUnavailable):
            review(memory,replace(OWNER,proposals=('approve',)),target='/api/hypotheses/synthetic-hypothesis/reject',
                note=None,request_id='synthetic-registered-review')
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(memory.get(OWNER,saved['reference'])['content'],marker)

    def test_invalid_and_cross_origin_requests_do_not_change_sources(self):
        self.seed()
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.post(self.native+'/api/hypotheses/synthetic-hypothesis/graduate',json={},
                headers={'Origin':'https://untrusted.invalid'})
            self.assertEqual(response.status_code,403,response.text)
            for body in ({'note':{}},{'target':'/other'},{'note':'x'*8193}):
                response=client.post(self.native+'/api/hypotheses/synthetic-hypothesis/graduate',json=body)
                self.assertEqual(response.status_code,400,response.text)
        self.assertEqual(self.snapshot(),before)

    def test_missing_fixture_tool_reports_pending_without_writing_memory(self):
        path=self.seed()
        path.write_text(path.read_text().replace('falsifier: Synthetic falsifier','falsifier: Synthetic falsifier\nenforcement_surface: hook')+
            '\n## Proposed Healing Fixture (RED '+chr(0x2014)+' proves the gap is real)\n'+
            'pending: `test/regression/pending/synthetic-fixture/`\n')
        before=self.snapshot()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.post(self.native+'/api/hypotheses/synthetic-hypothesis/graduate',json={})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['new_status'],'hypothesis')
            self.assertEqual(response.json()['patch'],'still-red-pending')
            self.assertIn('PromoteFixture',response.json()['patch_detail'])
        self.assertEqual(self.snapshot(),before)
