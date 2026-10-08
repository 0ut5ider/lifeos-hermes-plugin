# ABOUTME: Calls the actual native tab freshness server with synthetic metadata and owner sessions.
# ABOUTME: Checks native field fidelity, refused callers, retained sources, and cache invalidation.
import json
import os
from pathlib import Path
import subprocess
import unittest

import httpx
import test_memory_hypothesis_relay as queue_fixture
from test_memory_native import OWNER


class MemoryTabFreshnessTests(unittest.TestCase):
    native_module='tab-freshness.ts'
    setUp=queue_fixture.MemoryHypothesisRelayTests.setUp
    create_fixture=queue_fixture.MemoryHypothesisRelayTests.create_fixture
    native_module_name=queue_fixture.MemoryHypothesisRelayTests.native_module_name
    stop_dashboard=queue_fixture.MemoryHypothesisRelayTests.stop_dashboard
    stop_pulse=queue_fixture.MemoryHypothesisRelayTests.stop_pulse
    login=queue_fixture.MemoryHypothesisRelayTests.login

    def seed(self):
        path=self.root/'LIFEOS/USER/TELOS/TELOS.md'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('---\nlast_reviewed: 2026-10-08\n---\n# SyntheticTelosFreshnessMarker\n')
        return path

    def original(self,route):
        control=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script='import {handleRequest} from '+json.dumps(str(control/'LIFEOS/PULSE/modules/tab-freshness.ts'))+';'+\
            'const response=await handleRequest(new Request("http://127.0.0.1"+'+json.dumps(route)+'),"/api/tab-freshness");'+\
            'if(!response)throw new Error("Missing native response");console.log(JSON.stringify({status:response.status,body:await response.json()}));'
        result=subprocess.run(['bun','--no-install','-e',script],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,HOME=str(self.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),LIFEOS_MEMORY_INTERNAL='1'))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def test_owner_metadata_fields_match_native_for_selected_tabs(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in ('/api/tab-freshness?tab=telos','/api/tab-freshness?tab=assistant',
                    '/api/tab-freshness?tab=knowledge','/api/tab-freshness?tab=algorithm',
                    '/api/tab-freshness?tab=unknown','/api/tab-freshness'):
                expected=self.original(route)
                response=client.get(self.native+route)
                self.assertEqual({'status':response.status_code,'body':response.json()},expected)

    def test_anonymous_metadata_cannot_borrow_ambient_owner(self):
        self.seed()
        response=httpx.get(self.native+'/api/tab-freshness?tab=telos',headers={'X-LifeOS-Owner':'owner'},timeout=30)
        self.assertEqual(response.status_code,401,response.text)

    def test_revoked_owner_cannot_use_cached_metadata(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/tab-freshness?tab=telos').status_code,200)
            self.fixture.configuration.update(lambda value:value['accounts'].clear())
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.status_code,403,response.text)

    def test_current_owner_does_not_receive_stale_cached_review_date(self):
        path=self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/tab-freshness?tab=telos').json()['perFile'][0]['date'],'2026-10-08')
            path.write_text(path.read_text().replace('2026-10-08','2026-10-01'))
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.json()['perFile'][0]['date'],'2026-10-01')
            self.assertEqual(response.headers.get('cache-control'),'no-store')

    def test_private_source_does_not_publish_review_date(self):
        path=self.seed()
        path.write_text(path.read_text()+'\n<private>Synthetic private context</private>\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.status_code,200,response.text)
            self.assertIsNone(response.json()['perFile'][0]['date'])
        self.assertTrue(path.exists())

    def test_expanded_sources_and_empty_directories_preserve_native_metadata(self):
        directory=self.root/'LIFEOS/USER/TELOS/CURRENT_STATE'
        directory.mkdir(parents=True,exist_ok=True)
        (directory/'Synthetic.md').write_text('---\nlast_updated: 2026-10-02\n---\nSynthetic state\n')
        (directory/'Synthetic.json').write_text(json.dumps({'synthetic':'state'}))
        (directory/'Synthetic.yml').write_text('synthetic: state\n')
        empty=self.root/'LIFEOS/USER/TELOS/IDEAL_STATE'
        empty.mkdir(parents=True,exist_ok=True)
        (empty/'ignored.txt').write_text('Synthetic ignored text\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual({'status':response.status_code,'body':response.json()},self.original('/api/tab-freshness?tab=telos'))

    def test_directory_with_qualifying_nonfile_child_preserves_native_fallback(self):
        directory=self.root/'LIFEOS/USER/TELOS/CURRENT_STATE'
        (directory/'Synthetic.md').mkdir(parents=True,exist_ok=True)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual({'status':response.status_code,'body':response.json()},self.original('/api/tab-freshness?tab=telos'))

    def test_retired_source_and_dynamic_label_do_not_publish_metadata(self):
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        marker='SyntheticTabRetiredMarker'
        saved=memory.remember(OWNER,category='principal',content='RULE: '+marker,title='',project='',
            request_id='synthetic-tab-retained')
        path=self.root/'LIFEOS/USER/TELOS/CURRENT_STATE'/('SyntheticTabRetiredMarker.md')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('---\nlast_reviewed: 2026-10-08\n---\nSynthetic state\n')
        memory.forget(OWNER,saved['reference'],'synthetic-tab-retired')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.status_code,200,response.text)
            self.assertNotIn(marker,response.text)
        self.assertTrue(path.exists())

    def test_redirected_source_never_supplies_metadata(self):
        path=self.seed()
        outside=self.fixture.home/'outside-context.md'
        outside.write_text('---\nlast_reviewed: 2026-10-08\n---\nSynthetic outside state\n')
        path.unlink();path.symlink_to(outside)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.status_code,503,response.text)
        self.assertTrue(outside.exists())

    def test_connector_loss_refuses_cached_metadata(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/tab-freshness?tab=telos').status_code,200)
            (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native+'/api/tab-freshness?tab=telos').status_code,503)

    def test_origin_bearer_method_and_selectors_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/tab-freshness?tab=telos',
                headers={'Origin':'https://untrusted.invalid'}).status_code,403)
            self.assertEqual(client.get(self.native+'/api/tab-freshness?tab=telos',
                headers={'Authorization':'Bearer synthetic-invalid'}).status_code,401)
            self.assertEqual(client.post(self.native+'/api/tab-freshness?tab=telos',json={}).status_code,405)
            for route in ('/api/tab-freshness?tab=telos&tab=assistant','/api/tab-freshness?tab=../private',
                    '/api/tab-freshness?owner=other','/api/tab-freshness?tab='+('x'*65)):
                with self.subTest(route=route):self.assertEqual(client.get(self.native+route).status_code,400)

    def test_sources_timestamps_and_authority_are_rechecked_after_actual_render(self):
        import sys
        for mode in ('source','timestamp','authority'):
            with self.subTest(mode=mode):
                self.seed()
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_tab_freshness_process.py')),
                    str(self.fixture.configuration.path),mode],capture_output=True,text=True,timeout=40,
                    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})

    def test_each_registered_tab_preserves_native_owner_metadata(self):
        import shutil
        hooks=self.root/'hooks'
        if hooks.is_symlink():
            control=hooks.resolve()
            hooks.unlink();shutil.copytree(control,hooks)
        self.seed()
        tabs=('telos','work','health','finances','business','local','knowledge','hooks','algorithm','skills','agents',
            'docs','arbol','security','performance','synapse','ledger','assistant','gear','atlas')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for tab in tabs:
                with self.subTest(tab=tab):
                    route='/api/tab-freshness?tab='+tab
                    response=client.get(self.native+route)
                    self.assertEqual({'status':response.status_code,'body':response.json()},self.original(route))

    def test_source_byte_limit_refuses_metadata_without_raw_fallback(self):
        path=self.seed()
        path.write_text(path.read_text()+'x'*(256*1024))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.status_code,503,response.text)

    def test_private_json_source_metadata_is_excluded(self):
        path=self.root/'LIFEOS/USER/TELOS/LIFEOS_STATE.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'synthetic':'<private>Synthetic hidden state</private>'}))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.status_code,200,response.text)
            row=next(row for row in response.json()['perFile'] if row['name']=='LIFEOS_STATE.json')
            self.assertIsNone(row['date'])
        self.assertTrue(path.exists())

    def test_hardlinked_source_never_supplies_metadata(self):
        path=self.seed()
        outside=self.fixture.home/'linked-context.md'
        os.link(path,outside)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=telos')
            self.assertEqual(response.status_code,503,response.text)
        self.assertTrue(outside.exists())

    def test_unregistered_knowledge_filename_requires_source_admission(self):
        path=self.root/'LIFEOS/MEMORY/KNOWLEDGE/Ideas/SyntheticUnregisteredIdeaClaim.md'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('---\nlast_reviewed: 2026-10-08\n---\nSynthetic unregistered claim\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response=client.get(self.native+'/api/tab-freshness?tab=synapse')
            self.assertEqual(response.status_code,200,response.text)
            self.assertNotIn('SyntheticUnregisteredIdeaClaim',response.text)
        self.assertTrue(path.exists())

    def test_registered_knowledge_source_preserves_native_metadata(self):
        memory=self.fixture.fixture.fixture.fixture.fixture.memory
        saved=memory.remember(OWNER,category='project',content='Synthetic registered metadata idea',
            title='Synthetic registered idea',project='synthetic',request_id='synthetic-tab-registered')
        self.assertEqual(saved['status'],'committed',saved)
        with memory._transaction() as connection:
            row=connection.execute('SELECT path FROM records WHERE id=?',(saved['reference']['id'],)).fetchone()
            original=self.root/row['path']
            path=self.root/'LIFEOS/MEMORY/KNOWLEDGE/Ideas'/original.name
            path.parent.mkdir(parents=True,exist_ok=True)
            original.rename(path)
            connection.execute('UPDATE records SET path=? WHERE id=?',
                (path.relative_to(self.root).as_posix(),saved['reference']['id']))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            route='/api/tab-freshness?tab=synapse'
            response=client.get(self.native+route)
            self.assertEqual({'status':response.status_code,'body':response.json()},self.original(route))
